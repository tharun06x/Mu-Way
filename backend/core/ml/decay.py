"""
core/ml/decay.py — Skill Decay Modeling
=========================================
Skills fade over time when not practiced. This module computes a
time-adjusted mastery score that decays if a user hasn't touched a
domain recently, and flags "rusty" skills that need refreshing.

Formula:
    DecayedMastery(u, d) = RawMastery(u, d) × RetentionFactor(u, d)

    RetentionFactor = exp(-decay_rate × days_inactive_in_domain)
    
    Where:
      decay_rate = 0.005  (mastery halves ~every 139 days of inactivity)
      days_inactive = days since last submission in domain

Rust Threshold: RetentionFactor < 0.70 → domain is "rusty" (needs review)
"""

import logging
import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from core.config import settings as config

logger = logging.getLogger(__name__)

# Decay rate: skills lose ~0.5% per inactive day.
# At this rate mastery halves after ~139 days — realistic for tech skills.
DECAY_RATE: float = 0.005
RUST_THRESHOLD: float = 0.70   # RetentionFactor below this = "rusty"
RUST_DAYS_THRESHOLD: int = 60  # Minimum days of inactivity to consider rusty


@dataclass
class DomainDecayInfo:
    """Decay data for one user × domain."""
    domain: str
    raw_mastery: float
    days_inactive: int
    retention_factor: float
    decayed_mastery: float
    is_rusty: bool
    rust_severity: str  # 'NONE' | 'MILD' | 'MODERATE' | 'SEVERE'


@dataclass
class UserDecayProfile:
    """Full decay profile for one user."""
    user_id: str
    domains: dict[str, DomainDecayInfo] = field(default_factory=dict)
    rusty_domains: list[str] = field(default_factory=list)
    overall_retention: float = 1.0

    def to_dict(self) -> dict:
        return {
            'user_id': self.user_id,
            'overall_retention': round(self.overall_retention, 4),
            'rusty_domains': self.rusty_domains,
            'domains': {
                k: {
                    'raw_mastery':       round(v.raw_mastery, 4),
                    'decayed_mastery':   round(v.decayed_mastery, 4),
                    'days_inactive':     v.days_inactive,
                    'retention_factor':  round(v.retention_factor, 4),
                    'is_rusty':          v.is_rusty,
                    'rust_severity':     v.rust_severity,
                }
                for k, v in self.domains.items()
            },
        }


def _retention_factor(days_inactive: int, decay_rate: float = DECAY_RATE) -> float:
    """Exponential retention: exp(-rate × days)."""
    return float(math.exp(-decay_rate * max(0, days_inactive)))


def _rust_severity(retention: float) -> str:
    if retention >= RUST_THRESHOLD:
        return 'NONE'
    if retention >= 0.50:
        return 'MILD'
    if retention >= 0.30:
        return 'MODERATE'
    return 'SEVERE'


def compute_decay_profile(
    user_id: str,
    raw_mastery: dict,          # {domain: mastery_score}
    user_submissions: pd.DataFrame,   # full submission history for this user
    ref: pd.Timestamp | None = None,
) -> UserDecayProfile:
    """
    Compute decay-adjusted mastery for all domains of a single user.

    Args:
        user_id         : user identifier
        raw_mastery     : {domain: float} from features.py
        user_submissions: filtered DataFrame of this user's submissions
        ref             : reference timestamp (default: now)

    Returns:
        UserDecayProfile with per-domain decay info
    """
    ref = ref or pd.Timestamp.now()
    if ref.tzinfo is not None:
        ref = ref.tz_localize(None)

    profile = UserDecayProfile(user_id=user_id)

    # Build per-domain last-submission date
    last_dates: dict[str, int] = {}
    if not user_submissions.empty and 'domain_mapped' in user_submissions.columns:
        dates = pd.to_datetime(user_submissions['submission_date'])
        if dates.dt.tz is not None:
            dates = dates.dt.tz_convert('UTC').dt.tz_localize(None)
        user_submissions = user_submissions.copy()
        user_submissions['_days_ago'] = (ref - dates).dt.days.clip(lower=0)

        for dom, grp in user_submissions.groupby('domain_mapped'):
            last_dates[dom] = int(grp['_days_ago'].min())

    retention_values = []
    for dom, mastery in raw_mastery.items():
        # If user has no submissions in this domain, use a large inactivity value
        # but only if raw mastery is > 0 (to avoid penalising cold-start zeros)
        days_inactive = last_dates.get(dom, 0 if mastery == 0.0 else 365)

        retention = _retention_factor(days_inactive)
        decayed = float(np.clip(mastery * retention, 0.0, 1.0))
        is_rusty = (
            retention < RUST_THRESHOLD
            and mastery > 0.10              # Not rusty if never learned
            and days_inactive >= RUST_DAYS_THRESHOLD
        )

        info = DomainDecayInfo(
            domain=dom,
            raw_mastery=mastery,
            days_inactive=days_inactive,
            retention_factor=retention,
            decayed_mastery=decayed,
            is_rusty=is_rusty,
            rust_severity=_rust_severity(retention) if mastery > 0.10 else 'NONE',
        )
        profile.domains[dom] = info
        if is_rusty:
            profile.rusty_domains.append(dom)
        retention_values.append(retention)

    profile.overall_retention = float(np.mean(retention_values)) if retention_values else 1.0
    return profile


def apply_decay_to_features(
    user_features: dict,
    user_submissions: pd.DataFrame,
    ref: pd.Timestamp | None = None,
) -> tuple[dict, UserDecayProfile]:
    """
    Apply decay to a user's feature dictionary (output of compute_user_features).
    Returns the updated feature dict and the full decay profile.

    This is a drop-in wrapper: call this AFTER compute_user_features() to get
    decay-adjusted mastery values before passing to the ranking/gap pipelines.
    """
    raw_mastery = {
        dom: float(user_features.get(f'mastery_{dom}', 0.0))
        for dom in config.DOMAINS
    }

    user_id = user_features.get('user_id', 'unknown')
    profile = compute_decay_profile(user_id, raw_mastery, user_submissions, ref)

    # Overwrite mastery values with decayed versions
    updated = dict(user_features)
    for dom, info in profile.domains.items():
        updated[f'mastery_{dom}'] = info.decayed_mastery

    return updated, profile
