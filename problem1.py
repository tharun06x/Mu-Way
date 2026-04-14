"""
Problem 1 — Feature Engineering
=================================
Converts raw submission events → 40-column numerical feature vector per user.

Feature Groups (40 total):
  [5]  Global  : engagement_score, global_approval_rate, optimal_difficulty,
                 total_submissions, experience_level
  [8]  Mastery : mastery_{domain}        — time-decayed, difficulty-weighted
  [8]  Approval: approval_conf_{domain}  — Bayesian smoothed rate
  [8]  Count   : task_count_{domain}     — raw domain activity
  [8]  Interest: interest_{domain}       — normalised domain share
  [3]  Extra   : days_since_last, is_cold_start, approved_count

Formulas (from spec):
  MasteryScore   = Σ[approved × diff × λ^days_ago] / Σ[diff × λ^days_ago]
  ApprovalConf   = (PRIOR + approvals) / (PRIOR_TOTAL + attempts)
  EngagementScore= log(1+N_30) × (days_since_last+1)^(-0.5)
"""

import pandas as pd
import numpy as np
import logging
import config

logger = logging.getLogger(__name__)

DOMAINS      = config.DOMAINS
DECAY_LAMBDA = config.DECAY_LAMBDA
PRIOR_A      = config.BAYESIAN_PRIOR_APPROVALS
PRIOR_T      = config.BAYESIAN_PRIOR_TOTAL


# ─────────────────────────────────────────────────────────────────────────── #
#  Domain / Difficulty Mapping                                                #
# ─────────────────────────────────────────────────────────────────────────── #

_DOMAIN_TOKEN_MAP = {
    'ai': 'ai', 'ml': 'ai', 'genai': 'ai', 'logistic': 'ai',
    'linreg': 'ai', 'logreg': 'ai',
    'ds': 'ds', 'da': 'ds',
    'web': 'web', 'react': 'web', 'firebase': 'web',
    'javascript': 'web', 'frontend': 'web', 'beweb': 'web',
    'dsa': 'dsa', 'algorithm': 'dsa',
    'dop': 'devops', 'devops': 'devops', 'docker': 'devops',
    'cybersec': 'cybersec', 'security': 'cybersec',
    'android': 'android', 'flutter': 'android',
    'dart': 'android', 'kotlin': 'android',
}

_STRUCTURAL = {
    'ge', 'cl', 'lp24', 'lp25', 'lp', 'evn', 'daily',
    'pathway', 'intro', 'to', 'the', 'a',
}


def hashtag_to_domain(hashtag: str) -> str:
    """Map a hashtag string to one of the 8 canonical domains."""
    if pd.isna(hashtag) or str(hashtag).strip() == '':
        return 'general'
    tag = str(hashtag).lstrip('#').lower()
    for part in tag.split('-'):
        if part in _STRUCTURAL:
            continue
        if part in _DOMAIN_TOKEN_MAP:
            return _DOMAIN_TOKEN_MAP[part]
    return 'general'


def karma_to_difficulty(karma) -> int:
    """Map karma value → difficulty level 1-4."""
    if pd.isna(karma) or karma <= 0:  return 1
    if karma <= 30:   return 1
    if karma <= 100:  return 2
    if karma <= 300:  return 3
    return 4


# ─────────────────────────────────────────────────────────────────────────── #
#  Per-Metric Helpers                                                         #
# ─────────────────────────────────────────────────────────────────────────── #

def _mastery(group: pd.DataFrame, ref: pd.Timestamp) -> float:
    """
    MasteryScore(u,d) = Σ[approved × diff × λ^days_ago]
                       / Σ[diff × λ^days_ago]
    """
    days  = (ref - pd.to_datetime(group['submission_date'])).dt.days.clip(lower=0)
    decay = DECAY_LAMBDA ** days
    diff  = group.get('difficulty_level', pd.Series(2, index=group.index)).fillna(2)
    w_num = (group['is_approved'] * diff * decay).sum()
    w_den = (diff * decay).sum()
    return float(np.clip(w_num / w_den, 0, 1)) if w_den > 0 else 0.0


def _approval_conf(group: pd.DataFrame) -> float:
    """ApprovalConf(u,d) = (PRIOR + approvals) / (PRIOR_TOTAL + attempts)."""
    return float((PRIOR_A + group['is_approved'].sum()) / (PRIOR_T + len(group)))


def _engagement(user_df: pd.DataFrame, ref: pd.Timestamp) -> float:
    """EngagementScore = log(1+N_30) × (days_since_last+1)^(-0.5)."""
    days  = (ref - pd.to_datetime(user_df['submission_date'])).dt.days.clip(lower=0)
    n_30  = int((days <= 30).sum())
    d_last = float(days.min())
    return float(np.log1p(n_30) * (d_last + 1) ** (-0.5))


def _experience_level(total: int) -> int:
    if total < 10:   return 1
    if total < 30:   return 2
    if total < 100:  return 3
    return 4


# ─────────────────────────────────────────────────────────────────────────── #
#  Single-User Feature Vector                                                 #
# ─────────────────────────────────────────────────────────────────────────── #

def compute_user_features(
    user_id: str,
    user_data: pd.DataFrame,
    reference_date=None,
    task_data: pd.DataFrame = None,
) -> dict:
    """
    Build the 40-column feature vector for one user.

    Args:
        user_id       : identifier
        user_data     : rows belonging to this user
        reference_date: point-in-time reference (defaults to now)
        task_data     : task catalog for difficulty lookup

    Returns:
        dict  — one key per feature + 'user_id'
    """
    ref = pd.Timestamp(reference_date) if reference_date else pd.Timestamp.now()
    df  = user_data.copy()

    # Map domain
    df['domain_mapped'] = df['domain'].apply(hashtag_to_domain)

    # Attach difficulty from catalog if missing
    if 'difficulty_level' not in df.columns or df['difficulty_level'].isna().all():
        if task_data is not None:
            d_map = task_data.set_index('task_name')['difficulty_level'].to_dict()
            df['difficulty_level'] = df['task_name'].map(d_map).fillna(2).astype(int)
        else:
            df['difficulty_level'] = 2

    total = len(df)
    feat  = {'user_id': user_id}

    # ── Global features ──────────────────────────────────────────────── #
    feat['total_submissions']  = total
    feat['experience_level']   = _experience_level(total)
    feat['global_approval_rate'] = _approval_conf(df)
    feat['engagement_score']   = _engagement(df, ref)

    approved = df[df['is_approved'] == 1]
    feat['optimal_difficulty'] = (
        float(approved['difficulty_level'].mean()) + 0.5
        if len(approved) > 0 else 1.5
    )

    # ── Per-domain features (8 domains × 4 = 32) ─────────────────────── #
    by_domain = df.groupby('domain_mapped')

    for dom in DOMAINS:
        if dom in by_domain.groups:
            grp = by_domain.get_group(dom)
            feat[f'mastery_{dom}']      = _mastery(grp, ref)
            feat[f'approval_conf_{dom}'] = _approval_conf(grp)
            feat[f'task_count_{dom}']   = len(grp)
            feat[f'interest_{dom}']     = min(len(grp) / max(total, 1), 1.0)
        else:
            feat[f'mastery_{dom}']      = 0.0
            feat[f'approval_conf_{dom}'] = float(PRIOR_A / PRIOR_T)
            feat[f'task_count_{dom}']   = 0
            feat[f'interest_{dom}']     = 0.0

    # ── Extra features ────────────────────────────────────────────────── #
    dates = pd.to_datetime(df['submission_date'])
    feat['days_since_last_submission'] = int((ref - dates.max()).days)
    feat['is_cold_start']  = int(total < config.WARM_UP_THRESHOLD)
    feat['approved_count'] = int(df['is_approved'].sum())

    return feat


# ─────────────────────────────────────────────────────────────────────────── #
#  Feature Store Builder                                                      #
# ─────────────────────────────────────────────────────────────────────────── #

def build_feature_store(
    user_data: pd.DataFrame,
    task_data: pd.DataFrame = None,
    reference_date=None,
    save: bool = True,
) -> pd.DataFrame:
    """
    Build the feature store for ALL users.

    Key optimisation: group user_data once → O(n) instead of O(n×u).

    Returns:
        DataFrame with one row per user, 43 feature columns.
    """
    ref = pd.Timestamp(reference_date) if reference_date else pd.Timestamp.now()
    logger.info(
        f"Building feature store for {user_data['user_id'].nunique():,} users ..."
    )

    user_groups = dict(list(user_data.groupby('user_id')))
    total       = len(user_groups)
    all_feats   = []

    for i, (uid, grp) in enumerate(user_groups.items()):
        try:
            all_feats.append(compute_user_features(uid, grp, ref, task_data))
        except Exception as exc:
            logger.warning(f"Skipping {uid}: {exc}")

        if (i + 1) % 5000 == 0:
            logger.info(f"  … {i+1:,}/{total:,} users processed")

    feat_df = pd.DataFrame(all_feats)
    logger.info(
        f"✓ Feature store: {len(feat_df):,} users × {len(feat_df.columns)} features"
    )

    if save:
        feat_df.to_pickle(config.FEATURE_STORE_FILE)
        logger.info(f"✓ Saved → {config.FEATURE_STORE_FILE}")

    return feat_df


# ─────────────────────────────────────────────────────────────────────────── #
#  Single-User Lookup (used by downstream problems)                           #
# ─────────────────────────────────────────────────────────────────────────── #

def get_user_features(
    user_id: str,
    feature_store: pd.DataFrame = None,
    user_data: pd.DataFrame = None,
    task_data: pd.DataFrame = None,
) -> dict:
    """
    Return feature vector for one user.
    Priority: feature_store → on-the-fly compute → cold-start defaults.
    """
    if feature_store is not None:
        row = feature_store[feature_store['user_id'] == user_id]
        if len(row):
            return row.iloc[0].to_dict()

    if user_data is not None:
        rows = user_data[user_data['user_id'] == user_id]
        if len(rows):
            return compute_user_features(user_id, rows, task_data=task_data)

    logger.warning(f"Cold-start defaults for unknown user: {user_id}")
    feat = {
        'user_id': user_id,
        'total_submissions': 0,
        'experience_level': 1,
        'global_approval_rate': 0.5,
        'engagement_score': 0.0,
        'optimal_difficulty': 1.5,
        'days_since_last_submission': 999,
        'is_cold_start': 1,
        'approved_count': 0,
    }
    for dom in DOMAINS:
        feat[f'mastery_{dom}']       = 0.0
        feat[f'approval_conf_{dom}'] = 0.5
        feat[f'task_count_{dom}']    = 0
        feat[f'interest_{dom}']      = 0.0
    return feat


# ─────────────────────────────────────────────────────────────────────────── #
#  Standalone run                                                              #
# ─────────────────────────────────────────────────────────────────────────── #

if __name__ == '__main__':
    import logging as _log
    _log.basicConfig(
        level=_log.INFO,
        format='%(asctime)s %(levelname)s %(message)s',
    )

    from data_loader import DataLoader

    loader = DataLoader()
    user_data, task_data, _ = loader.load_all()

    feat_df = build_feature_store(user_data, task_data)

    print('\n=== Feature Store Sample (first user) ===')
    print(feat_df.iloc[0].to_string())
    print(f'\nTotal features : {len(feat_df.columns)}')
    print(f'Total users    : {len(feat_df):,}')
