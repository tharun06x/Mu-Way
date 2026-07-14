"""
core/services/achievements_service.py — Achievement & Streak System
===================================================================
Computes gamification data for the user: streaks, milestones, XP,
and badges — purely from their submission history.

No database required — all computed on-the-fly from user_submissions.
"""

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta

import pandas as pd

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────── #
#  Data Contracts                                                             #
# ─────────────────────────────────────────────────────────────────────────── #

@dataclass
class Badge:
    id: str
    name: str
    description: str
    icon: str          # emoji
    earned: bool
    earned_date: str | None = None

    def to_dict(self) -> dict:
        return {
            'id':           self.id,
            'name':         self.name,
            'description':  self.description,
            'icon':         self.icon,
            'earned':       self.earned,
            'earned_date':  self.earned_date,
        }


@dataclass
class AchievementProfile:
    user_id: str
    xp: int
    level: int
    level_title: str
    xp_to_next_level: int
    current_streak_days: int
    longest_streak_days: int
    total_approved: int
    total_submitted: int
    active_days: int
    badges: list[Badge] = field(default_factory=list)
    next_milestone: str = ''

    def to_dict(self) -> dict:
        return {
            'user_id':              self.user_id,
            'xp':                   self.xp,
            'level':                self.level,
            'level_title':          self.level_title,
            'xp_to_next_level':     self.xp_to_next_level,
            'current_streak_days':  self.current_streak_days,
            'longest_streak_days':  self.longest_streak_days,
            'total_approved':       self.total_approved,
            'total_submitted':      self.total_submitted,
            'active_days':          self.active_days,
            'badges':               [b.to_dict() for b in self.badges],
            'next_milestone':       self.next_milestone,
        }


# ─────────────────────────────────────────────────────────────────────────── #
#  XP & Level System                                                          #
# ─────────────────────────────────────────────────────────────────────────── #

# XP per approved submission by difficulty level
XP_PER_DIFFICULTY = {1: 10, 2: 25, 3: 50, 4: 100}

# Level thresholds: (min_xp, title)
LEVELS = [
    (0,    'Beginner',      ),
    (100,  'Explorer',      ),
    (300,  'Learner',       ),
    (600,  'Practitioner',  ),
    (1000, 'Developer',     ),
    (1800, 'Engineer',      ),
    (3000, 'Senior Engineer'),
    (5000, 'Expert',        ),
    (8000, 'Master',        ),
    (999999, 'Legend',      ),
]


def _compute_xp(approved_submissions: pd.DataFrame) -> int:
    """Sum XP from approved submissions weighted by difficulty."""
    if approved_submissions.empty:
        return 0
    xp = 0
    for _, row in approved_submissions.iterrows():
        diff = int(float(row.get('difficulty_level', 2)))
        diff = max(1, min(4, diff))
        xp += XP_PER_DIFFICULTY.get(diff, 25)
    return xp


def _get_level(xp: int) -> tuple[int, str, int]:
    """Return (level_number, level_title, xp_to_next)."""
    level_num = 1
    level_title = 'Beginner'
    xp_to_next = LEVELS[1][0] - xp if len(LEVELS) > 1 else 0

    for i, (threshold, title) in enumerate(LEVELS):
        if xp >= threshold:
            level_num = i + 1
            level_title = title
            next_threshold = LEVELS[i + 1][0] if i + 1 < len(LEVELS) else threshold
            xp_to_next = max(0, next_threshold - xp)

    return level_num, level_title, xp_to_next


def _compute_streak(submission_dates: pd.Series) -> tuple[int, int]:
    """
    Compute current and longest activity streaks in days.
    A "streak day" is any calendar day with at least one submission.

    Returns (current_streak, longest_streak).
    """
    if submission_dates.empty:
        return 0, 0

    dates = pd.to_datetime(submission_dates)
    if dates.dt.tz is not None:
        dates = dates.dt.tz_convert('UTC').dt.tz_localize(None)

    unique_days = sorted(set(dates.dt.date.tolist()), reverse=True)
    today = date.today()

    # Current streak: consecutive days ending today or yesterday
    current = 0
    if unique_days and unique_days[0] in (today, today - timedelta(days=1)):
        expected = unique_days[0]
        for d in unique_days:
            if d == expected:
                current += 1
                expected -= timedelta(days=1)
            else:
                break

    # Longest streak: global max
    longest = 0
    streak = 1
    for i in range(1, len(unique_days)):
        if (unique_days[i - 1] - unique_days[i]).days == 1:
            streak += 1
            longest = max(longest, streak)
        else:
            streak = 1
    longest = max(longest, current, streak)

    return current, longest


# ─────────────────────────────────────────────────────────────────────────── #
#  Badge Definitions                                                          #
# ─────────────────────────────────────────────────────────────────────────── #

def _evaluate_badges(
    total_approved: int,
    total_submitted: int,
    current_streak: int,
    longest_streak: int,
    unique_domains: int,
    xp: int,
) -> list[Badge]:
    """Return list of all badges with earned=True/False."""
    definitions = [
        Badge('first_task',     'First Step',       'Complete your first task',                 '🌱', total_approved >= 1),
        Badge('ten_tasks',      'Getting Started',  'Complete 10 tasks',                        '🎯', total_approved >= 10),
        Badge('fifty_tasks',    'Half Century',     'Complete 50 tasks',                        '⭐', total_approved >= 50),
        Badge('century',        'Century',          'Complete 100 tasks',                       '💯', total_approved >= 100),
        Badge('streak_7',       'Week Warrior',     '7-day submission streak',                  '🔥', current_streak >= 7),
        Badge('streak_30',      'Monthly Master',   '30-day submission streak',                 '🗓️', current_streak >= 30),
        Badge('multidomain',    'Polymath',         'Submit tasks in 5+ domains',               '🧠', unique_domains >= 5),
        Badge('high_approval',  'Quality First',    '80%+ approval rate on 20+ submissions',    '✅', total_submitted >= 20 and (total_approved / max(1, total_submitted)) >= 0.80),
        Badge('xp_500',         'Rising Star',      'Earn 500 XP',                              '⚡', xp >= 500),
        Badge('xp_2000',        'Expert Learner',   'Earn 2000 XP',                             '🏆', xp >= 2000),
        Badge('xp_5000',        'Legend',           'Earn 5000 XP',                             '👑', xp >= 5000),
        Badge('comeback',       'Comeback Kid',     'Return after 14+ days and submit a task',  '🔄', False),  # Set externally
    ]

    # Set earned_date for earned badges (approximate — not stored, so use "today")
    today_str = str(date.today())
    for badge in definitions:
        if badge.earned:
            badge.earned_date = today_str  # placeholder; real impl would query submission dates

    return definitions


# ─────────────────────────────────────────────────────────────────────────── #
#  Main Entry Point                                                           #
# ─────────────────────────────────────────────────────────────────────────── #

def compute_achievements(
    user_id: str,
    user_submissions: pd.DataFrame,
) -> AchievementProfile:
    """
    Compute the full achievement profile for a user.

    Args:
        user_id         : user identifier
        user_submissions: all submissions for this user (not just approved)

    Returns:
        AchievementProfile
    """
    if user_submissions is None or user_submissions.empty:
        return AchievementProfile(
            user_id=user_id, xp=0, level=1, level_title='Beginner',
            xp_to_next_level=100, current_streak_days=0, longest_streak_days=0,
            total_approved=0, total_submitted=0, active_days=0,
            badges=_evaluate_badges(0, 0, 0, 0, 0, 0),
            next_milestone='Complete your first task to start your journey!',
        )

    approved = user_submissions[user_submissions['is_approved'] == 1]
    total_approved = len(approved)
    total_submitted = len(user_submissions)

    xp = _compute_xp(approved)
    level, level_title, xp_to_next = _get_level(xp)
    current_streak, longest_streak = _compute_streak(user_submissions['submission_date'])

    unique_days = pd.to_datetime(user_submissions['submission_date']).dt.date.nunique()
    unique_domains = user_submissions.get('domain_mapped', user_submissions.get('domain', pd.Series())).nunique()

    badges = _evaluate_badges(
        total_approved, total_submitted,
        current_streak, longest_streak,
        unique_domains, xp,
    )

    # Next milestone message
    if total_approved < 10:
        next_milestone = f"{10 - total_approved} more approved tasks to earn 'Getting Started' badge! 🎯"
    elif total_approved < 50:
        next_milestone = f"{50 - total_approved} more approved tasks to earn 'Half Century' badge! ⭐"
    elif current_streak < 7:
        next_milestone = f"Submit for {7 - current_streak} more consecutive days to earn 'Week Warrior'! 🔥"
    elif xp_to_next > 0:
        next_milestone = f"Earn {xp_to_next} more XP to reach level {level + 1}: {LEVELS[min(level, len(LEVELS)-1)][1]}!"
    else:
        next_milestone = "You're a Legend! Keep inspiring others. 👑"

    return AchievementProfile(
        user_id=user_id,
        xp=xp,
        level=level,
        level_title=level_title,
        xp_to_next_level=xp_to_next,
        current_streak_days=current_streak,
        longest_streak_days=longest_streak,
        total_approved=total_approved,
        total_submitted=total_submitted,
        active_days=unique_days,
        badges=badges,
        next_milestone=next_milestone,
    )
