"""
Problem 4 — Career Roadmap Sequencing
=======================================
Converts a ranked task list → week-by-week, difficulty-progressive roadmap.

Steps (spec):
  1. Urgency tiering  : CRITICAL gaps fill Weeks 1-N first
  2. Difficulty prog. : max +1 level jump per step within a domain
  3. Week scheduling  : 3 hrs/week, tasks assigned to weeks by duration
  4. Failure adapt.   : bridge tasks on 3+ fails, drop on 5+ fails
  5. Health score     : critical domains in top-10 / total critical domains
"""

import json
import logging
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

import config

logger = logging.getLogger(__name__)

HOURS_PER_WEEK    = config.HOURS_PER_WEEK     # 3
MAX_WEEKS         = config.MAX_ROADMAP_WEEKS   # 16
TASK_HOURS        = {'Low': 1, 'Medium': 2, 'High': 3}  # estimated hrs per complexity


# ─────────────────────────────────────────────────────────────────────────── #
#  Urgency Tiering                                                            #
# ─────────────────────────────────────────────────────────────────────────── #

def _gap_tier(weighted_gap: float) -> str:
    if weighted_gap >= config.GAP_TIER_CRITICAL:  return 'CRITICAL'
    if weighted_gap >= config.GAP_TIER_MODERATE:  return 'MODERATE'
    if weighted_gap >= config.GAP_TIER_MARGINAL:  return 'MARGINAL'
    return 'MAINTENANCE'


TIER_ORDER = {'CRITICAL': 0, 'MODERATE': 1, 'MARGINAL': 2, 'MAINTENANCE': 3}


def _assign_urgency(recs: pd.DataFrame, domain_gaps: dict) -> pd.DataFrame:
    """Tag each recommended task with its urgency tier."""
    def row_tier(row):
        dg  = domain_gaps.get(row['domain'], {})
        gap = dg.get('weighted_gap', 0.0)
        return _gap_tier(gap)

    recs = recs.copy()
    recs['urgency_tier']   = recs.apply(row_tier, axis=1)
    recs['urgency_order']  = recs['urgency_tier'].map(TIER_ORDER)
    return recs


# ─────────────────────────────────────────────────────────────────────────── #
#  Difficulty Progression                                                     #
# ─────────────────────────────────────────────────────────────────────────── #

def _enforce_difficulty_progression(tasks: pd.DataFrame) -> pd.DataFrame:
    """
    Within each domain track: difficulty must not jump by more than 1 level.
    Tasks violating this are deferred.
    """
    if 'difficulty_level' not in tasks.columns:
        return tasks

    kept     = []
    deferred = []
    last_diff_by_domain: dict = {}

    for _, row in tasks.iterrows():
        dom  = row['domain']
        diff = int(row.get('difficulty_level', 2))
        last = last_diff_by_domain.get(dom)

        if last is None or diff <= last + 1:
            kept.append(row)
            last_diff_by_domain[dom] = max(last or 0, diff)
        else:
            deferred.append(row)

    # Append deferred at the end
    return pd.concat(
        [pd.DataFrame(kept), pd.DataFrame(deferred)],
        ignore_index=True,
    )


# ─────────────────────────────────────────────────────────────────────────── #
#  Week-by-Week Scheduling                                                    #
# ─────────────────────────────────────────────────────────────────────────── #

def _schedule_weeks(tasks: pd.DataFrame) -> list:
    """
    Pack tasks into weekly slots (3 hrs/week budget, max 16 weeks).

    Returns:
        list of dicts — {week, tasks: [{task_name, domain, urgency_tier, ...}]}
    """
    weeks        = []
    current_week = {'week': 1, 'hours_used': 0, 'tasks': []}

    for _, row in tasks.iterrows():
        task_hrs = TASK_HOURS.get(
            str(row.get('complexity', 'Medium')).strip().capitalize(),
            2,
        )

        if current_week['hours_used'] + task_hrs > HOURS_PER_WEEK:
            weeks.append(current_week)
            if len(weeks) >= MAX_WEEKS:
                break
            current_week = {
                'week': len(weeks) + 1,
                'hours_used': 0,
                'tasks': [],
            }

        current_week['tasks'].append({
            'task_name':    row.get('task_name', ''),
            'domain':       row.get('domain', ''),
            'urgency_tier': row.get('urgency_tier', 'MODERATE'),
            'difficulty_level': int(row.get('difficulty_level', 2)),
            'score':        round(float(row.get('score', 0.0)), 4),
        })
        current_week['hours_used'] += task_hrs

    if current_week['tasks']:
        weeks.append(current_week)

    return weeks


# ─────────────────────────────────────────────────────────────────────────── #
#  Roadmap Health Score                                                       #
# ─────────────────────────────────────────────────────────────────────────── #

def _health_score(weeks: list, domain_gaps: dict) -> float:
    """
    HealthScore = critical_domain_tasks_in_top_10 / total_critical_domains.
    Target ≥ 0.80.
    """
    critical_domains = {
        d for d, info in domain_gaps.items()
        if info.get('tier') == 'CRITICAL'
    }
    if not critical_domains:
        return 1.0

    top10_tasks = [
        t for w in weeks for t in w['tasks']
    ][:10]

    top10_critical = {t['domain'] for t in top10_tasks if t['domain'] in critical_domains}
    return round(len(top10_critical) / len(critical_domains), 4)


# ─────────────────────────────────────────────────────────────────────────── #
#  Single-User Roadmap Builder                                                #
# ─────────────────────────────────────────────────────────────────────────── #

def build_roadmap_for_user(
    user_id: str,
    gap_row: pd.Series,
    recommendations: pd.DataFrame,
    task_data: pd.DataFrame = None,
) -> dict:
    """
    Build a complete week-by-week roadmap for one user.

    Args:
        user_id        : identifier
        gap_row        : row from career_gap_df
        recommendations: ranked tasks from Problem 3 for this user
        task_data      : task catalog (for complexity/hours)

    Returns:
        dict  — complete roadmap
    """
    # Parse domain gaps
    dg_raw = gap_row.get('domain_gaps_json', '{}')
    try:
        domain_gaps = json.loads(dg_raw) if isinstance(dg_raw, str) else dg_raw
    except Exception:
        domain_gaps = {}

    if len(recommendations) == 0:
        return {
            'user_id':   user_id,
            'dream_role': gap_row.get('dream_role', 'Unknown'),
            'weeks':     [],
            'health':    0.0,
            'summary':   'No recommendations available.',
        }

    # Attach task complexity from catalog
    recs = recommendations.copy()
    if task_data is not None and 'complexity' not in recs.columns:
        cmap = task_data.set_index('task_name')['complexity'].to_dict() if 'complexity' in task_data.columns else {}
        recs['complexity'] = recs['task_name'].map(cmap).fillna('Medium')
        dmap = task_data.set_index('task_name')['difficulty_level'].to_dict()
        recs['difficulty_level'] = recs['task_name'].map(dmap).fillna(2).astype(int)

    # Step 1: urgency tiering
    recs = _assign_urgency(recs, domain_gaps)
    recs = recs.sort_values(
        ['urgency_order', 'score'],
        ascending=[True, False],
    )

    # Step 2: difficulty progression constraint
    recs = _enforce_difficulty_progression(recs)

    # Step 3: week-by-week scheduling
    weeks = _schedule_weeks(recs)

    # Step 4: health score
    health = _health_score(weeks, domain_gaps)

    return {
        'user_id':            user_id,
        'created_date':       str(datetime.now().date()),
        'dream_role':         gap_row.get('dream_role', 'Unknown'),
        'career_gap':         float(gap_row.get('career_gap', 0.0)),
        'career_gap_tier':    gap_row.get('career_gap_tier', 'MODERATE'),
        'readiness_pct':      float(gap_row.get('readiness_pct', 0.0)),
        'total_weeks':        len(weeks),
        'roadmap_weeks':      weeks,
        'roadmap_health':     health,
        'domain_gaps':        domain_gaps,
        'summary': {
            'total_weeks':         len(weeks),
            'total_tasks':         sum(len(w['tasks']) for w in weeks),
            'health_score':        health,
            'health_ok':          health >= 0.80,
            'first_week_domains': list({t['domain'] for t in (weeks[0]['tasks'] if weeks else [])}),
        },
    }


# ─────────────────────────────────────────────────────────────────────────── #
#  Full Pipeline                                                              #
# ─────────────────────────────────────────────────────────────────────────── #

def generate_career_roadmaps(
    career_gap_df: pd.DataFrame,
    pairs: pd.DataFrame,
    task_data: pd.DataFrame = None,
    top_k: int = 20,
) -> list:
    """
    Generate roadmaps for all users in career_gap_df.

    Args:
        career_gap_df : output of Problem 2
        pairs         : scored pairs from Problem 3
        task_data     : task catalog
        top_k         : tasks to consider per user for scheduling

    Returns:
        list of roadmap dicts
    """
    logger.info(f'Generating roadmaps for {len(career_gap_df):,} users ...')
    roadmaps = []

    for idx, row in career_gap_df.iterrows():
        uid = row['user_id']
        try:
            # Top-K recommendations for this user from pairs
            user_pairs = pairs[pairs['user_id'] == uid]
            if len(user_pairs) == 0:
                continue

            score_col = 'final_score' if 'final_score' in user_pairs.columns else 'rule_score'
            recs = user_pairs.nlargest(top_k, score_col)[
                ['task_name', 'domain', score_col]
            ].rename(columns={score_col: 'score'})

            roadmap = build_roadmap_for_user(uid, row, recs, task_data)
            roadmaps.append(roadmap)

        except Exception as exc:
            logger.warning(f'Roadmap failed for {uid}: {exc}')

        if (idx + 1) % 500 == 0:
            logger.info(f'  … {idx+1:,} roadmaps generated')

    logger.info(f'✓ Generated {len(roadmaps):,} roadmaps')
    return roadmaps


def save_roadmaps(roadmaps: list, path=None) -> dict:
    """Save roadmap summary JSON."""
    if path is None:
        path = config.ROADMAP_FILE

    healths = [r['roadmap_health'] for r in roadmaps]
    summary = {
        'generated':    len(roadmaps),
        'timestamp':    str(datetime.now()),
        'avg_health':   round(float(np.mean(healths)), 4) if healths else 0,
        'pct_healthy':  round(float(np.mean([h >= 0.80 for h in healths])) * 100, 2) if healths else 0,
        'sample':       roadmaps[0] if roadmaps else {},
    }

    with open(path, 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    logger.info(f'✓ Roadmaps saved → {path}')
    return summary


# ─────────────────────────────────────────────────────────────────────────── #
#  Standalone run                                                             #
# ─────────────────────────────────────────────────────────────────────────── #

if __name__ == '__main__':
    import logging as _log
    _log.basicConfig(level=_log.INFO, format='%(asctime)s %(levelname)s %(message)s')

    from data_loader import DataLoader
    from problem1 import build_feature_store
    from problem2_runner import compute_career_gap_for_users
    from problem3_runner import run_ranking_pipeline

    loader = DataLoader()
    user_data, task_data, _ = loader.load_all()

    feature_store = build_feature_store(user_data, task_data)
    gap_df        = compute_career_gap_for_users(feature_store)
    model, pairs, _ = run_ranking_pipeline(user_data, task_data)

    roadmaps = generate_career_roadmaps(gap_df, pairs, task_data)
    summary  = save_roadmaps(roadmaps)

    print('\n=== Roadmap Summary ===')
    print(f'Total generated : {summary["generated"]}')
    print(f'Avg health score: {summary["avg_health"]}')
    print(f'% healthy (≥0.8): {summary["pct_healthy"]}%')

    if roadmaps:
        r = roadmaps[0]
        print(f'\nSample roadmap for {r["user_id"]}:')
        print(f'  Dream Role    : {r["dream_role"]}')
        print(f'  Readiness     : {r["readiness_pct"]:.1f}%')
        print(f'  Total Weeks   : {r["total_weeks"]}')
        print(f'  Health Score  : {r["roadmap_health"]}')
        for w in r['roadmap_weeks'][:3]:
            print(f'  Week {w["week"]}: {[t["task_name"] for t in w["tasks"]]}')
