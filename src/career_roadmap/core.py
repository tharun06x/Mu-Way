"""Shared data structures and constants for the roadmap system."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


try:
    import config as legacy_config

    CANONICAL_DOMAINS = tuple(legacy_config.DOMAINS)
    ROLE_REQUIREMENTS = legacy_config.ROLE_REQUIREMENTS
except Exception:
    CANONICAL_DOMAINS = (
        "ai",
        "ds",
        "web",
        "dsa",
        "devops",
        "cybersec",
        "android",
        "general",
    )
    ROLE_REQUIREMENTS: dict[str, dict[str, tuple[float, float]]] = {}


@dataclass(frozen=True)
class UserFeatures:
    """Feature vector for one community member."""

    user_id: str
    total_submissions: int = 0
    engagement_score: float = 0.0
    global_approval_rate: float = 0.5
    optimal_difficulty: float = 1.5
    mastery: dict[str, float] = field(default_factory=dict)
    approval_confidence: dict[str, float] = field(default_factory=dict)
    task_counts: dict[str, int] = field(default_factory=dict)
    interests: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class ScheduledTask:
    """Task scheduled inside a roadmap week."""

    task_name: str
    domain: str
    week: int
    difficulty_level: int
    urgency_tier: str
    score: float
    reason: str = ""


@dataclass(frozen=True)
class Roadmap:
    """Week-by-week learning plan."""

    user_id: str
    dream_role: str
    readiness_pct: float
    total_weeks: int
    tasks: list[ScheduledTask] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
