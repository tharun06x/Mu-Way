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
import re
from pathlib import Path
import config
from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)

DOMAINS      = config.DOMAINS
DECAY_LAMBDA = config.DECAY_LAMBDA
PRIOR_A      = config.BAYESIAN_PRIOR_APPROVALS
PRIOR_T      = config.BAYESIAN_PRIOR_TOTAL


# ─────────────────────────────────────────────────────────────────────────── #
#  Schema Validation                                                          #
# ─────────────────────────────────────────────────────────────────────────── #

class SubmissionSchema(BaseModel):
    """Pydantic schema for individual submission validation."""
    user_id: str
    is_approved: int = Field(ge=0, le=1)
    
def validate_data(df: pd.DataFrame):
    """Validate required columns exist and have correct types/bounds using Pandas (fast for batch)."""
    required = ['user_id', 'is_approved', 'submission_date']
    for col in required:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")
    
    if not df['is_approved'].isin([0, 1]).all():
        raise ValueError("is_approved must be 0 or 1")
    
    if 'difficulty_level' in df.columns:
        # Accept floats (Bayesian-smoothed difficulty) — just ensure they are in [1, 4]
        valid_diffs = pd.to_numeric(df['difficulty_level'], errors='coerce').dropna()
        if len(valid_diffs) > 0 and not valid_diffs.between(1.0, 4.0).all():
            out_of_range = valid_diffs[~valid_diffs.between(1.0, 4.0)]
            raise ValueError(
                f"difficulty_level must be in [1.0, 4.0]; "
                f"found {len(out_of_range)} out-of-range values: {out_of_range.values[:5]}"
            )

# ─────────────────────────────────────────────────────────────────────────── #
#  Domain / Difficulty Mapping                                                #
# ─────────────────────────────────────────────────────────────────────────── #

def hashtag_to_domain(hashtag: str) -> str:
    """Map a hashtag string to one of the canonical domains using robust regex splitting."""
    if pd.isna(hashtag) or str(hashtag).strip() == '':
        return 'general'
    tag = str(hashtag).lstrip('#').lower()
    # Split by hyphen or underscore or space using regex
    for part in re.split(r'[-_\s]+', tag):
        if part in config.STRUCTURAL_TOKENS:
            continue
        if part in config.DOMAIN_TOKEN_MAP:
            return config.DOMAIN_TOKEN_MAP[part]
    return 'general'


def karma_to_difficulty(karma) -> float:
    """Map karma value → difficulty level 1-4."""
    if pd.isna(karma) or karma <= 0:  return 1.0
    if karma <= 30:   return 1.0
    if karma <= 100:  return 2.0
    if karma <= 300:  return 3.0
    return 4.0


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
    dates = pd.to_datetime(user_df['submission_date'])
    # Normalise to UTC-naive to avoid cross-tz arithmetic errors (BUG-6 fix)
    if dates.dt.tz is not None:
        dates = dates.dt.tz_convert('UTC').dt.tz_localize(None)
    ref_naive = ref.replace(tzinfo=None) if ref.tzinfo is not None else ref
    days  = (ref_naive - dates).dt.days.clip(lower=0)
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

def get_cold_start_features(user_id: str) -> dict:
    """Returns a dictionary with cold-start default features for an unknown user."""
    feat = {
        'user_id': user_id,
        'total_submissions': 0,
        'experience_level': 1,
        'global_approval_rate': float(PRIOR_A / PRIOR_T),
        'engagement_score': 0.0,
        'optimal_difficulty': 1.5,
        'days_since_last_submission': 999,
        'is_cold_start': 1,
        'approved_count': 0,
    }
    for dom in DOMAINS:
        feat[f'mastery_{dom}']       = 0.0
        feat[f'approval_conf_{dom}'] = float(PRIOR_A / PRIOR_T)
        feat[f'task_count_{dom}']    = 0
        feat[f'interest_{dom}']      = 0.0
    return feat


def compute_user_features(
    user_id: str,
    user_data: pd.DataFrame,
    ref: pd.Timestamp
) -> dict:
    """
    Build the 40-column feature vector for one user.
    Assumes user_data is ALREADY preprocessed (dates filtered, domains mapped, difficulties filled).
    """
    if len(user_data) == 0:
        return get_cold_start_features(user_id)

    df = user_data
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
            feat[f'mastery_{dom}']       = _mastery(grp, ref)
            feat[f'approval_conf_{dom}'] = _approval_conf(grp)
            feat[f'task_count_{dom}']    = len(grp)
            feat[f'interest_{dom}']      = min(len(grp) / max(total, 1), 1.0)
        else:
            feat[f'mastery_{dom}']       = 0.0
            feat[f'approval_conf_{dom}'] = float(PRIOR_A / PRIOR_T)
            feat[f'task_count_{dom}']    = 0
            feat[f'interest_{dom}']      = 0.0

    # ── Extra features ────────────────────────────────────────────────── #
    dates = pd.to_datetime(df['submission_date'])
    feat['days_since_last_submission'] = max(0, int((ref - dates.max()).days))  # BUG-2 fix: clamp to >= 0
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
    existing_store: pd.DataFrame = None,
    max_cache_age_hours: float = 24.0,
) -> pd.DataFrame:
    """
    Build the feature store for ALL users, supporting incremental updates.

    Persistent caching: if FEATURE_STORE_FILE exists and is younger than
    max_cache_age_hours (default 24 h), it is loaded directly to skip the
    expensive rebuild step (~60 s for 30 k users).
    Pass max_cache_age_hours=0 to force a full rebuild.
    """
    import time as _time

    ref = pd.Timestamp(reference_date) if reference_date else pd.Timestamp.now()

    # ── Persistent cache check ──────────────────────────────────────────────── #
    cache_file = config.FEATURE_STORE_FILE
    if (
        existing_store is None
        and max_cache_age_hours > 0
        and Path(cache_file).exists()
    ):
        age_hours = (_time.time() - Path(cache_file).stat().st_mtime) / 3600
        if age_hours < max_cache_age_hours:
            try:
                cached = pd.read_pickle(cache_file)
                logger.info(
                    f"✓ Loaded feature store from cache ({age_hours:.1f}h old) "
                    f"→ {len(cached):,} users × {len(cached.columns)} features"
                )
                return cached
            except Exception as exc:
                logger.warning(f"Cache load failed ({exc}), rebuilding ...")

    # 1. Schema Validation
    validate_data(user_data)
    
    df = user_data.copy()
    
    # 2. Vectorized Preprocessing (done globally instead of per-user)
    df['submission_date'] = pd.to_datetime(df['submission_date'], errors='coerce')
    df = df.dropna(subset=['submission_date'])
    df = df[df['submission_date'] <= ref]
    
    if 'is_team_member' in df.columns:
        # Fix explicit boolean casting bug
        df = df[~df['is_team_member'].isin([True, 1, 'true', 'True', 'Yes', 'yes'])]
        
    df['domain_mapped'] = df['domain'].apply(hashtag_to_domain)
    
    if 'difficulty_level' not in df.columns or df['difficulty_level'].isna().all():
        if task_data is not None:
            d_map = task_data.set_index('task_name')['difficulty_level'].to_dict()
            df['difficulty_level'] = df['task_name'].map(d_map).fillna(2.0).astype(float)
        else:
            df['difficulty_level'] = 2.0
    else:
        df['difficulty_level'] = df['difficulty_level'].fillna(2.0).astype(float)
        
    # 3. Incremental Update Filtering
    if existing_store is not None:
        # BUG-1 fix: filter to users ALREADY in the store (not all new users)
        if existing_store.index.name == 'user_id':
            store_user_ids = set(existing_store.index.tolist())
        else:
            store_user_ids = set(existing_store['user_id'].tolist())
        df = df[df['user_id'].isin(store_user_ids)]
    
    logger.info(f"Building features for {df['user_id'].nunique():,} users ...")

    # 4. GroupBy Iteration without OOM dict-cast
    all_feats = []
    user_groups = df.groupby('user_id')
    total = user_groups.ngroups
    
    for i, (uid, grp) in enumerate(user_groups):
        try:
            all_feats.append(compute_user_features(uid, grp, ref))
        except Exception as exc:
            logger.error(f"Error computing features for {uid}: {exc}. Using defaults.")
            all_feats.append(get_cold_start_features(uid))
            
        if (i + 1) % 5000 == 0:
            logger.info(f"  … {i+1:,}/{total:,} users processed")

    new_feat_df = pd.DataFrame(all_feats)
    if 'user_id' in new_feat_df.columns:
        new_feat_df.set_index('user_id', inplace=True)
        
    # 5. Merge with existing store
    if existing_store is not None:
        if existing_store.index.name != 'user_id' and 'user_id' in existing_store.columns:
            existing_store.set_index('user_id', inplace=True)
            
        existing_store.update(new_feat_df)
        
        new_users = new_feat_df[~new_feat_df.index.isin(existing_store.index)]
        if not new_users.empty:
            existing_store = pd.concat([existing_store, new_users])
            
        feat_df = existing_store
    else:
        feat_df = new_feat_df

    logger.info(f"✓ Feature store: {len(feat_df):,} users × {len(feat_df.columns)} features")

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
    Return feature vector for one user using O(1) index lookup.
    Priority: feature_store → on-the-fly compute → cold-start defaults.
    """
    if feature_store is not None:
        if feature_store.index.name == 'user_id':
            if user_id in feature_store.index:
                row = feature_store.loc[user_id].to_dict()
                row['user_id'] = user_id
                return row
        else:
            # Fallback if not indexed
            row_df = feature_store[feature_store['user_id'] == user_id]
            if len(row_df):
                return row_df.iloc[0].to_dict()

    if user_data is not None:
        rows = user_data[user_data['user_id'] == user_id]
        if len(rows):
            ref = pd.Timestamp.now()
            rows = rows.copy()
            rows['domain_mapped'] = rows['domain'].apply(hashtag_to_domain)
            if 'difficulty_level' not in rows.columns:
                if task_data is not None:
                    d_map = task_data.set_index('task_name')['difficulty_level'].to_dict()
                    rows['difficulty_level'] = rows['task_name'].map(d_map).fillna(2.0).astype(float)
                else:
                    rows['difficulty_level'] = 2.0
            return compute_user_features(user_id, rows, ref)

    logger.warning(f"Cold-start defaults for unknown user: {user_id}")
    return get_cold_start_features(user_id)


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
    if len(feat_df) > 0:
        print(feat_df.iloc[0].to_string())
    print(f'\nTotal features : {len(feat_df.columns)}')
    print(f'Total users    : {len(feat_df):,}')
