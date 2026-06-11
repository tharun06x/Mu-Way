"""
Problem 5 — Drift Monitoring & Feedback Loop
=============================================
Detects model/data degradation and triggers retraining.

Components (spec):
  1. Feature Drift     — Population Stability Index (PSI)
  2. Label Drift       — Kolmogorov-Smirnov test
  3. Approval Rate     — ±3σ control chart
  4. Churn Risk        — per-user behavioural scoring
  5. Community Health  — single aggregated score
  6. Retrain Engine    — decision logic

Churn Risk formula (spec):
  ChurnRisk = 0.40×inactivity + 0.25×rate_decline + 0.20×failure_streak + 0.15×career_gap
"""

import json
import logging
from datetime import datetime

import numpy as np
import pandas as pd

try:
    from scipy.stats import ks_2samp
except ImportError:
    def ks_2samp(a, b):
        a = np.sort(np.asarray(a, dtype=float))
        b = np.sort(np.asarray(b, dtype=float))
        if len(a) == 0 or len(b) == 0:
            return 0.0, 1.0
        values = np.sort(np.unique(np.concatenate([a, b])))
        cdf_a = np.searchsorted(a, values, side='right') / len(a)
        cdf_b = np.searchsorted(b, values, side='right') / len(b)
        stat = float(np.max(np.abs(cdf_a - cdf_b)))
        n_eff = len(a) * len(b) / (len(a) + len(b))
        p_value = float(min(1.0, 2.0 * np.exp(-2.0 * n_eff * stat * stat)))
        return stat, p_value

import config

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────── #
#  1. Feature Drift — PSI                                                     #
# ─────────────────────────────────────────────────────────────────────────── #

def compute_psi(baseline: np.ndarray, current: np.ndarray, bins: int = 10) -> float:
    """
    PSI = Σ (cur_pct - base_pct) × ln(cur_pct / base_pct)
    PSI < 0.10 : STABLE | 0.10-0.20 : WARN | > 0.20 : ALERT
    """
    if len(baseline) == 0 or len(current) == 0:
        return 0.0

    breakpoints = np.percentile(baseline, np.linspace(0, 100, bins + 1))

    def proportions(data):
        props = []
        for i in range(len(breakpoints) - 1):
            cnt = np.sum((data >= breakpoints[i]) & (data < breakpoints[i + 1]))
            props.append(cnt / len(data) + 1e-10)
        return np.array(props)

    b_props = proportions(baseline)
    c_props = proportions(current)
    return float(np.sum((c_props - b_props) * np.log(c_props / b_props)))


def psi_status(psi: float) -> dict:
    if psi < config.PSI_THRESHOLD_WARNING:
        return {'status': 'STABLE',  'action': 'No action'}
    if psi < config.PSI_THRESHOLD_ALERT:
        return {'status': 'WARN',    'action': 'Monitor closely'}
    return     {'status': 'ALERT',   'action': 'Retrain now'}


def run_feature_drift_detection(
    baseline_features: pd.DataFrame,
    current_features: pd.DataFrame,
) -> pd.DataFrame:
    records = []
    for col in baseline_features.columns:
        try:
            b = baseline_features[col].values.astype(float)
            c = current_features[col].values.astype(float)
            b = b[~np.isnan(b)]
            c = c[~np.isnan(c)]
            psi_val  = compute_psi(b, c)
            info     = psi_status(psi_val)
            records.append({'feature': col, 'psi': round(psi_val, 4), **info})
        except Exception as exc:
            records.append({'feature': col, 'psi': np.nan, 'status': 'ERROR', 'action': str(exc)})

    drift_df = pd.DataFrame(records).sort_values('psi', ascending=False).reset_index(drop=True)
    s = drift_df['status'].value_counts()
    logger.info(f'Feature drift: {s.get("STABLE",0)} stable, {s.get("WARN",0)} warn, {s.get("ALERT",0)} alert')
    return drift_df


# ─────────────────────────────────────────────────────────────────────────── #
#  2. Label Drift — KS Test                                                   #
# ─────────────────────────────────────────────────────────────────────────── #

def check_label_drift(baseline_labels, current_labels) -> dict:
    """p < 0.05 → significant drift → regenerate labels + retrain."""
    if len(baseline_labels) == 0 or len(current_labels) == 0:
        return {'ks_statistic': 0.0, 'p_value': 1.0,
                'drift_detected': False, 'status': 'SKIP', 'action': 'Insufficient data'}

    stat, p = ks_2samp(baseline_labels, current_labels)
    drift   = bool(p < 0.05)
    return {
        'ks_statistic':  round(float(stat), 4),
        'p_value':       round(float(p), 6),
        'drift_detected': drift,
        'status':        'ALERT' if drift else 'STABLE',
        'action':        'Regenerate labels + retrain' if drift else 'No action',
    }


# ─────────────────────────────────────────────────────────────────────────── #
#  3. Approval Rate Control Chart ±3σ                                         #
# ─────────────────────────────────────────────────────────────────────────── #

def build_control_chart(historical_rates: np.ndarray) -> dict:
    mu    = float(np.mean(historical_rates))
    sigma = float(np.std(historical_rates, ddof=1)) if len(historical_rates) > 1 else 0.05
    return {
        'mean':  round(mu, 4),
        'ucl':   round(mu + 3 * sigma, 4),
        'lcl':   round(max(0.0, mu - 3 * sigma), 4),
        'sigma': round(sigma, 4),
    }


def check_approval_rate(current_rate: float, historical_rates: np.ndarray) -> dict:
    chart     = build_control_chart(historical_rates)
    in_ctrl   = chart['lcl'] <= current_rate <= chart['ucl']
    return {
        'current_rate':  round(current_rate, 4),
        'control_chart': chart,
        'in_control':    in_ctrl,
        'status':        'STABLE' if in_ctrl else 'ALERT',
        'action':        'No action' if in_ctrl else 'Investigate approval process',
    }


# ─────────────────────────────────────────────────────────────────────────── #
#  4. Churn Risk — Per User                                                   #
# ─────────────────────────────────────────────────────────────────────────── #

def compute_churn_risk(
    user_data: pd.DataFrame,
    career_gap_df: pd.DataFrame = None,
    ref_date=None,
) -> pd.DataFrame:
    """
    ChurnRisk = 0.40×inactivity + 0.25×rate_decline + 0.20×failure_streak + 0.15×career_gap
    """
    ref = pd.Timestamp(ref_date) if ref_date else pd.Timestamp.now()

    gap_map = {}
    if career_gap_df is not None:
        gap_map = career_gap_df.set_index('user_id')['career_gap'].to_dict()

    records = []
    for uid, grp in user_data.groupby('user_id'):
        grp = grp.sort_values('submission_date')
        dates = pd.to_datetime(grp['submission_date'])

        days_inactive  = int((ref - dates.max()).days)
        inactivity     = min(days_inactive / 30.0, 1.0)

        approval_rate  = float(grp['is_approved'].mean())
        recent         = grp.tail(10)
        recent_rate    = float(recent['is_approved'].mean()) if len(recent) else approval_rate
        rate_decline   = max(0.0, approval_rate - recent_rate)

        fails_streak   = 0
        for approved in grp['is_approved'].iloc[::-1]:
            if approved == 0:
                fails_streak += 1
            else:
                break
        failure_streak = min(fails_streak / 5.0, 1.0)

        career_gap     = float(gap_map.get(uid, 0.35))

        churn = (
            0.40 * inactivity +
            0.25 * rate_decline +
            0.20 * failure_streak +
            0.15 * career_gap
        )
        churn = float(np.clip(churn, 0, 1))

        records.append({
            'user_id':      uid,
            'churn_risk':   round(churn, 3),
            'risk_level':   'HIGH' if churn >= 0.65 else 'MEDIUM' if churn >= 0.40 else 'LOW',
            'days_inactive': days_inactive,
        })

    churn_df = pd.DataFrame(records)
    logger.info(f'✓ Churn risk computed for {len(churn_df):,} users')
    return churn_df


# ─────────────────────────────────────────────────────────────────────────── #
#  5. Community Health Score                                                  #
# ─────────────────────────────────────────────────────────────────────────── #

def compute_community_health(
    psi_mean: float,
    ks_p_value: float,
    approval_rate: float,
    ndcg: float,
    churn_risk_mean: float,
) -> dict:
    """
    CommunityHealth (spec) uses weighted avg alignment, growth, approval, beginner_progression.
    We proxy with our 5 monitoring signals.
    """
    components = {
        'feature_drift': max(0.0, 1 - psi_mean / 0.25),
        'label_drift':   1.0 if ks_p_value > 0.05 else 0.5,
        'approval_rate': min(approval_rate / 0.70, 1.0),
        'ndcg':          min(ndcg / 0.85, 1.0),
        'churn_risk':    1.0 - churn_risk_mean,
    }

    score = sum(
        config.HEALTH_WEIGHTS[k] * v for k, v in components.items()
    )
    score = float(np.clip(score, 0, 1))

    status = 'CRITICAL'
    for s, (lo, hi) in config.HEALTH_SCORE_THRESHOLDS.items():
        if lo <= score <= hi:
            status = s
            break

    return {
        'community_health_score': round(score, 3),
        'status':     status,
        'components': {k: round(v, 3) for k, v in components.items()},
        'timestamp':  str(pd.Timestamp.now()),
    }


# ─────────────────────────────────────────────────────────────────────────── #
#  6. Retrain Decision Engine                                                 #
# ─────────────────────────────────────────────────────────────────────────── #

def retrain_decision_engine(
    psi_report=None,
    ks_result=None,
    approval_control=None,
    health_score=None,
    last_retrain_date=None,
) -> dict:
    signals = {'psi_alert': False, 'ks_alert': False,
               'approval_breached': False, 'health_dropped': False, 'interval_ready': True}
    reasons = []

    if psi_report is not None:
        n_alerts = int((psi_report['status'] == 'ALERT').sum())
        if n_alerts > 0:
            signals['psi_alert'] = True
            reasons.append(f'PSI alert on {n_alerts} feature(s)')

    if ks_result and ks_result.get('drift_detected'):
        signals['ks_alert'] = True
        reasons.append(f'Label drift (p={ks_result["p_value"]})')

    if approval_control and not approval_control.get('in_control', True):
        signals['approval_breached'] = True
        reasons.append(f'Approval rate {approval_control["current_rate"]} out of control')

    if health_score and health_score.get('status') in ('WARNING', 'CRITICAL'):
        signals['health_dropped'] = True
        reasons.append(f'Community health: {health_score["status"]}')

    if last_retrain_date:
        days = (pd.Timestamp.now() - pd.Timestamp(last_retrain_date)).days
        if days < config.RETRAIN_DECISION['min_retraining_interval_days']:
            signals['interval_ready'] = False
            reasons.append(f'Interval not met ({days}d < {config.RETRAIN_DECISION["min_retraining_interval_days"]}d)')

    alert_count = sum([signals['psi_alert'], signals['ks_alert'],
                       signals['approval_breached'], signals['health_dropped']])

    should_retrain = False
    confidence     = 'LOW'

    if alert_count >= 2 and signals['interval_ready']:
        should_retrain = True
        confidence     = 'HIGH' if alert_count >= 3 else 'MEDIUM'
    elif alert_count == 1 and signals['ks_alert'] and signals['interval_ready']:
        should_retrain = True
        confidence     = 'MEDIUM'

    urgency = (
        'HIGH'   if (signals['psi_alert'] or signals['ks_alert']) and should_retrain
        else 'MEDIUM' if should_retrain
        else 'NONE'
    )

    return {
        'should_retrain':     should_retrain,
        'urgency':            urgency,
        'confidence':         confidence,
        'signal_count':       alert_count,
        'signals':            signals,
        'reasons':            reasons,
        'recommended_action': 'RETRAIN ALL MODELS' if should_retrain else 'CONTINUE MONITORING',
        'timestamp':          str(pd.Timestamp.now()),
    }


# ─────────────────────────────────────────────────────────────────────────── #
#  Full Pipeline                                                              #
# ─────────────────────────────────────────────────────────────────────────── #

def run_drift_monitoring_pipeline(
    baseline_features: pd.DataFrame,
    current_features: pd.DataFrame,
    baseline_labels,
    current_labels,
    current_approval_rate: float,
    historical_approval_rates,
    current_ndcg: float,
    user_data: pd.DataFrame = None,
    career_gap_df: pd.DataFrame = None,
) -> dict:
    logger.info('Running Problem 5 — Drift Monitoring ...')

    psi_report      = run_feature_drift_detection(baseline_features, current_features)
    ks_result       = check_label_drift(baseline_labels, current_labels)
    approval_ctrl   = check_approval_rate(current_approval_rate, historical_approval_rates)

    if user_data is not None:
        churn_df        = compute_churn_risk(user_data, career_gap_df)
        churn_risk_mean = float(churn_df['churn_risk'].mean())
    else:
        churn_df        = None
        churn_risk_mean = 0.35

    health          = compute_community_health(
        psi_mean        = float(psi_report['psi'].mean()),
        ks_p_value      = ks_result['p_value'],
        approval_rate   = current_approval_rate,
        ndcg            = current_ndcg,
        churn_risk_mean = churn_risk_mean,
    )

    decision = retrain_decision_engine(
        psi_report       = psi_report,
        ks_result        = ks_result,
        approval_control = approval_ctrl,
        health_score     = health,
    )

    logger.info(f'Community health : {health["status"]} ({health["community_health_score"]})')
    logger.info(f'Retrain decision : {decision["recommended_action"]}')

    return {
        'psi_report':       psi_report,
        'ks_result':        ks_result,
        'approval_control': approval_ctrl,
        'churn_df':         churn_df,
        'health_report':    health,
        'retrain_decision': decision,
        'timestamp':        str(pd.Timestamp.now()),
    }


def save_monitoring_report(results: dict, path=None) -> dict:
    if path is None:
        path = config.HEALTH_REPORT_FILE

    psi = results['psi_report']
    report = {
        'timestamp':       results['timestamp'],
        'health':          results['health_report'],
        'psi_summary':     {
            'alerts':   int((psi['status'] == 'ALERT').sum()),
            'warnings': int((psi['status'] == 'WARN').sum()),
            'stable':   int((psi['status'] == 'STABLE').sum()),
        },
        'label_drift':     results['ks_result'],
        'approval_rate':   results['approval_control'],
        'retrain_decision': results['retrain_decision'],
    }

    with open(path, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    logger.info(f'✓ Monitoring report → {path}')
    return report


# ─────────────────────────────────────────────────────────────────────────── #
#  Standalone run (uses mock data — no real baseline needed)                  #
# ─────────────────────────────────────────────────────────────────────────── #

if __name__ == '__main__':
    import logging as _log
    _log.basicConfig(level=_log.INFO, format='%(asctime)s %(levelname)s %(message)s')

    rng = np.random.default_rng(42)

    baseline_feat = pd.DataFrame({
        'mastery':         rng.normal(0.60, 0.15, 500),
        'interest_score':  rng.uniform(0, 1, 500),
        'engagement':      rng.beta(2, 5, 500),
    })
    current_feat = pd.DataFrame({
        'mastery':         rng.normal(0.55, 0.18, 200),  # slight drift
        'interest_score':  rng.uniform(0, 1, 200),
        'engagement':      rng.beta(1.5, 6, 200),
    })

    baseline_labels = rng.choice([0, 1, 2, 3, 4], 800, p=[0.15, 0.30, 0.30, 0.15, 0.10])
    current_labels  = rng.choice([0, 1, 2, 3, 4], 300, p=[0.30, 0.35, 0.20, 0.10, 0.05])

    historical_rates = np.array([0.72, 0.74, 0.70, 0.73, 0.71, 0.75, 0.72, 0.74])
    current_rate     = 0.58  # anomalous

    results = run_drift_monitoring_pipeline(
        baseline_features         = baseline_feat,
        current_features          = current_feat,
        baseline_labels           = baseline_labels,
        current_labels            = current_labels,
        current_approval_rate     = current_rate,
        historical_approval_rates = historical_rates,
        current_ndcg              = 0.83,
    )

    report = save_monitoring_report(results)

    print('\n=== Drift Monitoring Report ===')
    print(f'Community health : {results["health_report"]["status"]} ({results["health_report"]["community_health_score"]})')
    print(f'Retrain decision : {results["retrain_decision"]["recommended_action"]}')
    print(f'Reasons          : {results["retrain_decision"]["reasons"]}')
    print(f'Churn risk df    : N/A (no user_data passed)')
