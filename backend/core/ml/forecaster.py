"""
core/ml/forecaster.py — Progress Forecasting & Adaptive Goals
==============================================================
Answers three questions that users desperately want to know:

  1. "How many weeks until I'm ready for my dream role?" 
       → ProgressForecast.weeks_to_goal

  2. "If I pick AI Engineer vs Full Stack, which is faster?"
       → compare_roles()

  3. "How many hours/week should I actually aim for?"
       → AdaptiveGoalEngine.compute_goal()

Formula for weeks_to_goal:
    remaining_gap = career_gap × (1 - readiness_pct/100)  [already computed by P2]
    gap_closed_per_week = avg_mastery_gain_per_week × avg_domain_weight
    weeks_to_goal = remaining_gap / gap_closed_per_week

    Clamped to [1, 52] weeks. If no history → default 20 weeks.
"""

import logging
import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from core.config import settings as config
from core.career_gap import compute_career_gap

logger = logging.getLogger(__name__)

# Conservative default: assume a user closes ~1.5% career gap per week
DEFAULT_WEEKLY_GAP_CLOSURE = 0.015
MIN_WEEKS = 1
MAX_WEEKS = 52

# Adaptive goal defaults
DEFAULT_HOURS_PER_WEEK = config.HOURS_PER_WEEK  # 3
MIN_HOURS = 1
MAX_HOURS = 10


# ─────────────────────────────────────────────────────────────────────────── #
#  Data Contracts                                                             #
# ─────────────────────────────────────────────────────────────────────────── #

@dataclass
class ProgressForecast:
    """The "how long until I get there" answer."""
    user_id: str
    dream_role: str
    current_readiness_pct: float
    career_gap: float
    weeks_to_goal: int
    estimated_completion_date: str
    weekly_gap_closure_rate: float
    confidence: str   # 'HIGH' | 'MEDIUM' | 'LOW'
    message: str

    def to_dict(self) -> dict:
        return {
            'user_id':                  self.user_id,
            'dream_role':               self.dream_role,
            'current_readiness_pct':    round(self.current_readiness_pct, 2),
            'career_gap':               round(self.career_gap, 4),
            'weeks_to_goal':            self.weeks_to_goal,
            'estimated_completion_date': self.estimated_completion_date,
            'weekly_gap_closure_rate':  round(self.weekly_gap_closure_rate, 4),
            'confidence':               self.confidence,
            'message':                  self.message,
        }


@dataclass
class RoleComparisonResult:
    """Side-by-side comparison of two career paths."""
    role_a: str
    role_b: str
    gap_a: dict   # full career gap for role A
    gap_b: dict   # full career gap for role B
    forecast_a: ProgressForecast
    forecast_b: ProgressForecast
    recommendation: str
    shared_domains: list[str]
    switching_cost_weeks: int   # extra weeks if user switches from A→B

    def to_dict(self) -> dict:
        return {
            'role_a':               self.role_a,
            'role_b':               self.role_b,
            'gap_a':                self.gap_a,
            'gap_b':                self.gap_b,
            'forecast_a':           self.forecast_a.to_dict(),
            'forecast_b':           self.forecast_b.to_dict(),
            'recommendation':       self.recommendation,
            'shared_domains':       self.shared_domains,
            'switching_cost_weeks': self.switching_cost_weeks,
        }


@dataclass
class AdaptiveGoal:
    """Personalised weekly hours goal."""
    recommended_hours: float
    recommended_tasks: int
    completion_rate_7d: float    # fraction of roadmap tasks completed last 7 days
    burnout_risk: str            # 'LOW' | 'MEDIUM' | 'HIGH'
    motivation: str              # short motivational message

    def to_dict(self) -> dict:
        return {
            'recommended_hours':   round(self.recommended_hours, 1),
            'recommended_tasks':   self.recommended_tasks,
            'completion_rate_7d':  round(self.completion_rate_7d, 3),
            'burnout_risk':        self.burnout_risk,
            'motivation':          self.motivation,
        }


# ─────────────────────────────────────────────────────────────────────────── #
#  Forecasting Engine                                                         #
# ─────────────────────────────────────────────────────────────────────────── #

def _estimate_weekly_closure(user_submissions: pd.DataFrame) -> tuple[float, str]:
    """
    Estimate how much career gap this user closes per week, based on their
    historical submission velocity and approval rate.

    Returns (weekly_closure_rate, confidence_level)
    """
    if user_submissions is None or user_submissions.empty:
        return DEFAULT_WEEKLY_GAP_CLOSURE, 'LOW'

    # Look at the last 8 weeks of activity
    ref = pd.Timestamp.now()
    if ref.tzinfo is not None:
        ref = ref.tz_localize(None)
    dates = pd.to_datetime(user_submissions['submission_date'])
    if dates.dt.tz is not None:
        dates = dates.dt.tz_convert('UTC').dt.tz_localize(None)

    days_ago = (ref - dates).dt.days.clip(lower=0)
    recent = user_submissions[days_ago <= 56].copy()  # 8 weeks

    if len(recent) == 0:
        return DEFAULT_WEEKLY_GAP_CLOSURE, 'LOW'

    # Approvals per week (as a proxy for mastery gain velocity)
    n_weeks_active = max(1, len(recent) / 7)  # rough week count
    approved_per_week = recent['is_approved'].sum() / n_weeks_active

    # Each approved task closes a small amount of gap (~0.5-2% depending on difficulty)
    avg_diff = float(recent.get('difficulty_level', pd.Series([2.0])).mean())
    gap_per_task = 0.005 * avg_diff     # heuristic: harder tasks close more gap

    weekly_closure = float(approved_per_week * gap_per_task)
    weekly_closure = max(0.005, min(0.08, weekly_closure))   # clamp to [0.5%, 8%]

    confidence = 'HIGH' if len(recent) >= 10 else ('MEDIUM' if len(recent) >= 4 else 'LOW')
    return weekly_closure, confidence


def compute_progress_forecast(
    user_id: str,
    gap_data: dict,
    user_submissions: pd.DataFrame | None = None,
) -> ProgressForecast:
    """
    Compute a forward-looking forecast: how many weeks to reach the dream role.

    Args:
        user_id        : user identifier
        gap_data       : output of compute_career_gap() — contains career_gap, readiness_pct, dream_role
        user_submissions: full submission history for velocity estimation

    Returns:
        ProgressForecast with weeks_to_goal and estimated_completion_date
    """
    career_gap = float(gap_data.get('career_gap', 0.5))
    readiness = float(gap_data.get('readiness_pct', 50.0))
    dream_role = gap_data.get('dream_role', 'Unknown')

    # Already job-ready!
    if readiness >= 90.0:
        return ProgressForecast(
            user_id=user_id,
            dream_role=dream_role,
            current_readiness_pct=readiness,
            career_gap=career_gap,
            weeks_to_goal=0,
            estimated_completion_date=str(pd.Timestamp.now().date()),
            weekly_gap_closure_rate=0.0,
            confidence='HIGH',
            message=f"🎉 You are already {readiness:.0f}% ready for {dream_role}! Start applying now.",
        )

    weekly_closure, confidence = _estimate_weekly_closure(user_submissions)

    # remaining_gap is the absolute gap still to close
    remaining_gap = career_gap
    if remaining_gap <= 0:
        weeks_raw = 1
    else:
        weeks_raw = math.ceil(remaining_gap / weekly_closure)

    weeks_to_goal = int(np.clip(weeks_raw, MIN_WEEKS, MAX_WEEKS))

    completion_date = (pd.Timestamp.now() + pd.Timedelta(weeks=weeks_to_goal)).date()

    # Build human message
    if weeks_to_goal <= 4:
        msg = f"🔥 You're very close! At your current pace, you'll be ready for {dream_role} in ~{weeks_to_goal} weeks."
    elif weeks_to_goal <= 12:
        msg = f"📈 You're making solid progress. {dream_role} is ~{weeks_to_goal} weeks away. Keep it up!"
    elif weeks_to_goal <= 26:
        msg = f"🎯 Your goal is {dream_role} in ~{weeks_to_goal} weeks. Consider dedicating more hours per week to accelerate."
    else:
        msg = f"🚀 {dream_role} is a big jump from where you are now (~{weeks_to_goal} weeks). Consider a bridging role first."

    return ProgressForecast(
        user_id=user_id,
        dream_role=dream_role,
        current_readiness_pct=readiness,
        career_gap=career_gap,
        weeks_to_goal=weeks_to_goal,
        estimated_completion_date=str(completion_date),
        weekly_gap_closure_rate=weekly_closure,
        confidence=confidence,
        message=msg,
    )


# ─────────────────────────────────────────────────────────────────────────── #
#  Multi-Role Comparison                                                      #
# ─────────────────────────────────────────────────────────────────────────── #

def compare_roles(
    user_id: str,
    user_mastery: dict,
    role_a: str,
    role_b: str,
    user_submissions: pd.DataFrame | None = None,
) -> RoleComparisonResult:
    """
    Compare two career paths side-by-side for a specific user.
    Returns gap analysis, forecasts, shared domains, and a recommendation.

    Args:
        user_id       : user identifier
        user_mastery  : {domain: mastery_score} from feature vector
        role_a        : first role name (must be in ROLE_REQUIREMENTS)
        role_b        : second role name (must be in ROLE_REQUIREMENTS)
        user_submissions: submission history for velocity estimation

    Returns:
        RoleComparisonResult with full side-by-side analysis
    """
    gap_a = compute_career_gap(user_mastery, role_a)
    gap_b = compute_career_gap(user_mastery, role_b)

    forecast_a = compute_progress_forecast(user_id, gap_a, user_submissions)
    forecast_b = compute_progress_forecast(user_id, gap_b, user_submissions)

    # Shared domains (skills that help both roles)
    domains_a = set(config.ROLE_REQUIREMENTS.get(role_a, {}).keys())
    domains_b = set(config.ROLE_REQUIREMENTS.get(role_b, {}).keys())
    shared = sorted(domains_a & domains_b)

    # Switching cost: extra weeks if user switches from A to B
    switching_weeks = max(0, forecast_b.weeks_to_goal - forecast_a.weeks_to_goal)

    # Recommendation logic
    if forecast_a.weeks_to_goal <= forecast_b.weeks_to_goal:
        faster_role = role_a
        faster_weeks = forecast_a.weeks_to_goal
        recommendation = (
            f"{role_a} is the faster path (~{faster_weeks} weeks) given your current skills. "
            f"You share {len(shared)} domain(s) with {role_b}, so skills transfer if you switch later."
        )
    else:
        faster_role = role_b
        faster_weeks = forecast_b.weeks_to_goal
        recommendation = (
            f"{role_b} is the faster path (~{faster_weeks} weeks) given your current skills. "
            f"You share {len(shared)} domain(s) with {role_a}, so skills transfer if you switch later."
        )

    if shared:
        recommendation += f" Shared domains: {', '.join(shared)}."

    return RoleComparisonResult(
        role_a=role_a,
        role_b=role_b,
        gap_a=gap_a,
        gap_b=gap_b,
        forecast_a=forecast_a,
        forecast_b=forecast_b,
        recommendation=recommendation,
        shared_domains=shared,
        switching_cost_weeks=abs(forecast_a.weeks_to_goal - forecast_b.weeks_to_goal),
    )


# ─────────────────────────────────────────────────────────────────────────── #
#  Adaptive Goal Engine                                                       #
# ─────────────────────────────────────────────────────────────────────────── #

class AdaptiveGoalEngine:
    """
    Personalizes the weekly learning goal (hours/tasks) based on actual
    completion history. Replaces the hardcoded 3h/week for all users.

    Burnout signals:
      - Approval rate < 50% in last 2 weeks → reduce goal
      - 0 submissions in last 7 days → re-engagement mode
      - Very high velocity (≥ 8 tasks/week approved) → encourage more
    """

    def __init__(self, base_hours: float = DEFAULT_HOURS_PER_WEEK):
        self.base_hours = base_hours

    def compute_goal(
        self,
        user_submissions: pd.DataFrame | None,
        career_gap_tier: str = 'MODERATE',
    ) -> AdaptiveGoal:
        """
        Compute the adaptive weekly goal for a user.

        Args:
            user_submissions : full submission history
            career_gap_tier  : 'CRITICAL' | 'MODERATE' | 'MARGINAL' | 'MET'

        Returns:
            AdaptiveGoal with recommended_hours, tasks, and motivation message
        """
        if user_submissions is None or user_submissions.empty:
            return self._default_goal(career_gap_tier)

        ref = pd.Timestamp.now()
        if ref.tzinfo is not None:
            ref = ref.tz_localize(None)
        dates = pd.to_datetime(user_submissions['submission_date'])
        if dates.dt.tz is not None:
            dates = dates.dt.tz_convert('UTC').dt.tz_localize(None)

        days_ago = (ref - dates).dt.days.clip(lower=0)

        # Last 7 days
        last_7 = user_submissions[days_ago <= 7]
        # Last 14 days
        last_14 = user_submissions[days_ago <= 14]

        n_7 = len(last_7)
        n_14 = len(last_14)
        approval_rate_14 = float(last_14['is_approved'].mean()) if n_14 > 0 else 0.7
        completion_rate = n_7 / 7.0   # tasks/day in last week

        # Burnout detection
        if n_7 == 0:
            # Completely inactive last week → re-engagement mode
            burnout_risk = 'HIGH'
            hours = 1.0
            tasks = 1
            motivation = "👋 Welcome back! Let's ease back in — just 1 task this week to rebuild momentum."
        elif approval_rate_14 < 0.40 and n_14 >= 4:
            # Low approval rate → tasks too hard, reduce pressure
            burnout_risk = 'HIGH'
            hours = max(MIN_HOURS, self.base_hours - 1.0)
            tasks = max(1, int(hours / 1.5))
            motivation = "💪 Tasks seem challenging lately — a lighter week will help you recharge and come back stronger."
        elif approval_rate_14 < 0.60 and n_14 >= 4:
            burnout_risk = 'MEDIUM'
            hours = self.base_hours
            tasks = max(1, int(hours / 1.5))
            motivation = "📚 Steady progress! Maintain your current pace and focus on understanding before moving up."
        elif completion_rate >= 1.0 and approval_rate_14 >= 0.70:
            # High velocity + high approval → user is crushing it, push more
            burnout_risk = 'LOW'
            extra = min(2.0, completion_rate * 0.5)
            hours = min(MAX_HOURS, self.base_hours + extra)
            tasks = max(2, int(hours / 1.5))
            motivation = f"🔥 You're on fire! You've been consistently completing tasks — push for {tasks} this week!"
        else:
            # Normal mode
            burnout_risk = 'LOW'
            hours = self.base_hours
            # Critical gap → nudge slightly more tasks
            if career_gap_tier == 'CRITICAL':
                hours = min(MAX_HOURS, hours + 0.5)
            tasks = max(1, int(hours / 1.5))
            motivation = "✅ You're making steady progress. Keep up your current momentum!"

        return AdaptiveGoal(
            recommended_hours=hours,
            recommended_tasks=tasks,
            completion_rate_7d=completion_rate,
            burnout_risk=burnout_risk,
            motivation=motivation,
        )

    def _default_goal(self, career_gap_tier: str) -> AdaptiveGoal:
        hours = self.base_hours
        if career_gap_tier == 'CRITICAL':
            hours += 0.5
        return AdaptiveGoal(
            recommended_hours=hours,
            recommended_tasks=max(1, int(hours / 1.5)),
            completion_rate_7d=0.0,
            burnout_risk='LOW',
            motivation="🚀 Let's get started! Completing even 1 task this week puts you ahead of most people.",
        )
