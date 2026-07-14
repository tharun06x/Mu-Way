"""
Problem 2 — Skill Gap Modeling
================================
Quantifies how far each user is from their dream role, per domain and overall.

Formulas (spec):
  GapScore(u,d,r)  = max(0, required_mastery - current_mastery) × weight
  CareerGap(u,r)   = Σ GapScore across all required domains
  AlignmentScore   = 1 - CareerGap                    (user-facing percentage)
  DomainAlignment  = min(1.0, current / required)     (per-domain progress bar)

Gap Tiers (spec):
  CRITICAL  ≥ 0.04   — roadmap leads with these
  MODERATE  0.01-0.04
  MARGINAL  0.001-0.01
  MET       < 0.001
"""

import json
import logging

import numpy as np
import pandas as pd

from core.config import settings as config
from core.features import hashtag_to_domain, get_user_features

logger = logging.getLogger(__name__)

ROLE_REQUIREMENTS = config.ROLE_REQUIREMENTS
DOMAIN_TO_ROLE    = config.DOMAIN_TO_ROLE


# ─────────────────────────────────────────────────────────────────────────── #
#  Helpers                                                                    #
# ─────────────────────────────────────────────────────────────────────────── #

def get_gap_tier(gap: float) -> str:
    if gap >= config.GAP_TIER_CRITICAL:  return 'CRITICAL'
    if gap >= config.GAP_TIER_MODERATE:  return 'MODERATE'
    if gap >= config.GAP_TIER_MARGINAL:  return 'MARGINAL'
    return 'MET'


def infer_dream_role(user_features: dict) -> str:
    """Infer dream role from a single user's feature dictionary."""
    if not user_features:
        return 'Full Stack Developer'

    counts = {d: float(user_features.get(f'task_count_{d}', 0)) for d in config.DOMAINS}
    
    # If all domain counts are 0, it's a cold start user
    if all(count == 0 for count in counts.values()):
        return 'Full Stack Developer'
        
    primary = max(counts, key=counts.get)
    return DOMAIN_TO_ROLE.get(primary, 'Full Stack Developer')


# ─────────────────────────────────────────────────────────────────────────── #
#  Core Gap Computation                                                       #
# ─────────────────────────────────────────────────────────────────────────── #

def compute_career_gap(user_mastery: dict, dream_role: str) -> dict:
    """
    Compute CareerGap and domain breakdown for one user.

    Args:
        user_mastery : {domain: mastery_score}
        dream_role   : role name (must exist in ROLE_REQUIREMENTS)

    Returns:
        dict with career_gap, alignment_score, tier, domain_gaps
    """
    if dream_role not in ROLE_REQUIREMENTS:
        dream_role = 'Full Stack Developer'

    requirements = ROLE_REQUIREMENTS[dream_role]
    domain_gaps  = {}
    total_gap    = 0.0

    for domain, (required, weight) in requirements.items():
        current = float(user_mastery.get(domain, 0.0))
        raw_gap = max(0.0, required - current)
        weighted_gap = raw_gap * weight

        domain_gaps[domain] = {
            'current':          round(current, 4),
            'required':         required,
            'raw_gap':          round(raw_gap, 4),
            'weighted_gap':     round(weighted_gap, 4),
            'tier':             get_gap_tier(weighted_gap),
            'domain_alignment': round(min(1.0, current / required) if required > 0 else 1.0, 4),
        }
        total_gap += weighted_gap

    total_gap      = float(np.clip(total_gap, 0.0, 1.0))
    # Clip alignment independently — it must also stay in [0, 1]
    alignment      = float(np.clip(1.0 - total_gap, 0.0, 1.0))
    readiness_pct  = round(100.0 * alignment, 2)

    return {
        'dream_role':          dream_role,
        'career_gap':          round(total_gap, 4),
        'alignment_score':     round(alignment, 4),
        'readiness_pct':       readiness_pct,
        'career_gap_tier':     get_gap_tier(total_gap),
        'domain_gaps':         domain_gaps,
        'domain_gaps_json':    json.dumps(domain_gaps),
    }


# ─────────────────────────────────────────────────────────────────────────── #
#  Pipeline                                                                   #
# ─────────────────────────────────────────────────────────────────────────── #

def run_skill_gap_pipeline(
    feature_store: pd.DataFrame,
    dream_roles: dict = None,
) -> pd.DataFrame:
    """
    Compute career gaps for every user in the feature store.

    B5 fix: Vectorized using NumPy matrix ops — ~10× faster than row-by-row apply().

    Args:
        feature_store : output of Problem 1 (one row per user)
        dream_roles   : optional {user_id: role_name} override dict

    Returns:
        DataFrame [user_id, dream_role, career_gap, alignment_score,
                   readiness_pct, career_gap_tier, domain_gaps_json]
    """
    logger.info(f"Running Problem 2 — Skill Gap for {len(feature_store):,} users ...")
    if dream_roles is None:
        dream_roles = {}

    if len(feature_store) == 0:
        return pd.DataFrame(columns=['user_id', 'dream_role', 'career_gap', 'alignment_score',
                                     'readiness_pct', 'career_gap_tier', 'domain_gaps_json'])

    # ── Step 1: Resolve dream role per user ──────────────────────────────── #
    fs = feature_store.copy()
    if fs.index.name == 'user_id':
        user_ids = fs.index.tolist()
        fs = fs.reset_index()
    else:
        user_ids = fs['user_id'].tolist()

    # Vectorized role inference: find argmax of task_count columns per row
    count_cols = [f'task_count_{d}' for d in config.DOMAINS if f'task_count_{d}' in fs.columns]
    if count_cols:
        counts_mat = fs[count_cols].values
        # BUG-3 fix: rows where ALL counts are 0 are cold-start users.
        # np.argmax([0,0,...,0]) returns 0 (first domain = 'ai'), which wrongly
        # assigns them as AI Engineers. Detect and route them to 'general' first.
        row_sums = counts_mat.sum(axis=1)
        dominant_domain_idx = counts_mat.argmax(axis=1)
        domain_names = [c.replace('task_count_', '') for c in count_cols]
        dominant_domains = [
            'general' if row_sums[i] == 0 else domain_names[dominant_domain_idx[i]]
            for i in range(len(dominant_domain_idx))
        ]
    else:
        dominant_domains = ['general'] * len(fs)

    roles = []
    for uid, dom in zip(user_ids, dominant_domains):
        role = dream_roles.get(uid)
        if role is None:
            role = DOMAIN_TO_ROLE.get(dom, 'Full Stack Developer')
        roles.append(role)

    fs['_dream_role'] = roles

    # ── Step 2: Fully vectorized gap computation per role group ──────────── #
    # BUG-9 fix: replaced iterrows() with matrix ops so this scales to 30k users
    records = []

    for role_name, group in fs.groupby('_dream_role'):
        requirements = ROLE_REQUIREMENTS.get(role_name, ROLE_REQUIREMENTS['Full Stack Developer'])
        req_domains  = list(requirements.keys())
        required_arr = np.array([requirements[d][0] for d in req_domains], dtype=float)
        weight_arr   = np.array([requirements[d][1] for d in req_domains], dtype=float)

        # Gather mastery matrix (users × domains)
        mastery_cols = [f'mastery_{d}' for d in req_domains]
        available    = [c for c in mastery_cols if c in group.columns]
        mastery_mat  = group[available].values.astype(float) if available else np.zeros((len(group), len(req_domains)))

        # Pad missing domain columns with 0
        if len(available) < len(req_domains):
            full_mat = np.zeros((len(group), len(req_domains)))
            for i, col in enumerate(mastery_cols):
                if col in group.columns:
                    full_mat[:, i] = group[col].values
            mastery_mat = full_mat

        raw_gaps     = np.maximum(0.0, required_arr - mastery_mat)          # (users × domains)
        weighted_gaps = raw_gaps * weight_arr                                # (users × domains)
        total_gaps   = np.clip(weighted_gaps.sum(axis=1), 0.0, 1.0)         # (users,)
        alignments   = np.clip(1.0 - total_gaps, 0.0, 1.0)

        uid_series = group.get('user_id', group.index.to_series())

        for i, (uid, total_gap, alignment) in enumerate(
            zip(uid_series, total_gaps, alignments)
        ):
            # Per-domain gap dict for this user
            domain_gaps = {}
            for j, domain in enumerate(req_domains):
                current  = float(mastery_mat[i, j])
                raw_gap  = float(raw_gaps[i, j])
                wgap     = float(weighted_gaps[i, j])
                required = required_arr[j]
                domain_gaps[domain] = {
                    'current':          round(current, 4),
                    'required':         required,
                    'raw_gap':          round(raw_gap, 4),
                    'weighted_gap':     round(wgap, 4),
                    'tier':             get_gap_tier(wgap),
                    'domain_alignment': round(
                        min(1.0, current / required) if required > 0 else 1.0, 4
                    ),
                }

            records.append({
                'user_id':          uid,
                'dream_role':       role_name,
                'career_gap':       round(float(total_gap), 4),
                'alignment_score':  round(float(alignment), 4),
                'readiness_pct':    round(100.0 * float(alignment), 2),
                'career_gap_tier':  get_gap_tier(float(total_gap)),
                'domain_gaps_json': json.dumps(domain_gaps),
            })

    df = pd.DataFrame(records)
    cols = ['user_id', 'dream_role', 'career_gap', 'alignment_score',
            'readiness_pct', 'career_gap_tier', 'domain_gaps_json']
    df = df[[c for c in cols if c in df.columns]]

    logger.info(
        f"✓ Career gaps computed | "
        f"Tier distribution:\n{df['career_gap_tier'].value_counts().to_string()}"
    )
    return df



def compute_career_gap_for_users(
    feature_store: pd.DataFrame,
    dream_roles: dict = None,
    output_file=None,
) -> pd.DataFrame:
    """Wrapper — runs pipeline and optionally saves CSV."""
    gap_df = run_skill_gap_pipeline(feature_store, dream_roles)
    if output_file:
        gap_df.to_csv(output_file, index=False)
        logger.info(f"✓ Saved → {output_file}")
    return gap_df


# ─────────────────────────────────────────────────────────────────────────── #
#  Standalone run                                                             #
# ─────────────────────────────────────────────────────────────────────────── #

if __name__ == '__main__':
    import logging as _log
    _log.basicConfig(level=_log.INFO, format='%(asctime)s %(levelname)s %(message)s')

    from data_loader import DataLoader
    from problem1 import build_feature_store

    loader = DataLoader()
    user_data, task_data, _ = loader.load_all()
    feature_store = build_feature_store(user_data, task_data)

    gap_df = compute_career_gap_for_users(
        feature_store, output_file=config.CAREER_GAP_FILE
    )

    print('\n=== Career Gap Results (first 5 users) ===')
    print(gap_df.head().to_string())
    print('\nCareer gap stats:')
    print(gap_df['career_gap'].describe())
    print('\nTier distribution:')
    print(gap_df['career_gap_tier'].value_counts())
