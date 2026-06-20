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

import config
from problem1 import hashtag_to_domain, get_user_features

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

    total_gap = float(np.clip(total_gap, 0, 1))

    return {
        'dream_role':          dream_role,
        'career_gap':          round(total_gap, 4),
        'alignment_score':     round(1.0 - total_gap, 4),
        'readiness_pct':       round(100 * (1.0 - total_gap), 2),
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

    results = []

    for idx, row in feature_store.iterrows():
        # Handle both indexed and non-indexed DataFrames safely
        user_id = row.get('user_id', idx)

        # Extract mastery vector from feature store
        user_mastery = {
            dom: float(row.get(f'mastery_{dom}', 0.0))
            for dom in config.DOMAINS
        }

        # Determine dream role
        role = dream_roles.get(user_id) or infer_dream_role(row.to_dict())

        gap = compute_career_gap(user_mastery, role)
        results.append({
            'user_id':          user_id,
            'dream_role':       gap['dream_role'],
            'career_gap':       gap['career_gap'],
            'alignment_score':  gap['alignment_score'],
            'readiness_pct':    gap['readiness_pct'],
            'career_gap_tier':  gap['career_gap_tier'],
            'domain_gaps_json': gap['domain_gaps_json'],
        })

    df = pd.DataFrame(results)
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
