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
from problem1 import hashtag_to_domain

logger = logging.getLogger(__name__)

HOURS_PER_WEEK    = config.HOURS_PER_WEEK     # 3
MAX_WEEKS         = config.MAX_ROADMAP_WEEKS   # 16
TASK_HOURS        = {'Low': 1, 'Medium': 2, 'High': 3}  # estimated hrs per complexity


def _normalize_task_name(value) -> str:
    if pd.isna(value):
        return ''
    return ' '.join(str(value).strip().lower().split())


# ─────────────────────────────────────────────────────────────────────────── #
#  Urgency Tiering                                                            #
# ─────────────────────────────────────────────────────────────────────────── #

def _gap_tier(weighted_gap: float) -> str:
    if weighted_gap >= config.GAP_TIER_CRITICAL:  return 'CRITICAL'
    if weighted_gap >= config.GAP_TIER_MODERATE:  return 'MODERATE'
    if weighted_gap >= config.GAP_TIER_MARGINAL:  return 'MARGINAL'
    return 'MET'  # B13 fix: align with problem2_runner.get_gap_tier() — was 'MAINTENANCE'


TIER_ORDER = {'CRITICAL': 0, 'MODERATE': 1, 'MARGINAL': 2, 'MET': 3}  # B13 fix: was MAINTENANCE


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
    Within each domain track: difficulty must not jump by more than 1 level up.
    Going down (easier tasks) is always allowed.
    Tasks violating the +1 cap are deferred.
    """
    if 'difficulty_level' not in tasks.columns:
        return tasks

    kept     = []
    last_diff_by_domain: dict = {}

    for _, row in tasks.iterrows():
        dom       = row['domain']
        diff_float = float(row.get('difficulty_level', 2.0))
        diff_tier  = int(diff_float)
        last_tier  = last_diff_by_domain.get(dom)

        # B11 fix: allow difficulty to go DOWN freely (easier tasks are always fine);
        # only cap upward jumps to +1 level at a time.
        if last_tier is None or diff_tier <= last_tier + 1:
            kept.append(row)
            last_diff_by_domain[dom] = diff_tier

    return pd.DataFrame(kept).reset_index(drop=True)


# ─────────────────────────────────────────────────────────────────────────── #
#  Week-by-Week Scheduling                                                    #
# ─────────────────────────────────────────────────────────────────────────── #

def _schedule_weeks(tasks: pd.DataFrame) -> list:
    """
    Pack tasks into weekly slots (3 hrs/week budget, max 16 weeks).
    All time stored as MINUTES for consistent display.
    Applies noise reduction: max 4 tasks/week, max 2 tasks/domain/week,
    and CRITICAL urgency blocks MODERATE tasks.

    Returns:
        list of dicts — {week, minutes_used, tasks: [{task_name, domain, urgency_tier, ...}]}
    """
    MINUTES_PER_WEEK = config.HOURS_PER_WEEK * 60   # 3 h * 60 = 180 min
    TASK_MINUTES = {'Low': 60, 'Medium': 120, 'High': 180}

    weeks = []
    tasks_to_schedule = tasks.to_dict('records')

    while tasks_to_schedule and len(weeks) < MAX_WEEKS:
        current_week = {'week': len(weeks) + 1, 'minutes_used': 0, 'tasks': []}
        deferred_tasks = []
        week_domains = {}
        has_critical = False

        for row in tasks_to_schedule:
            task_mins = TASK_MINUTES.get(
                str(row.get('complexity', 'Medium')).strip().capitalize(),
                120,
            )
            domain = row.get('domain', '')
            urgency = row.get('urgency_tier', 'MODERATE')

            # --- Constraints ---
            if current_week['minutes_used'] + task_mins > MINUTES_PER_WEEK:
                deferred_tasks.append(row)
                continue
            if len(current_week['tasks']) >= 4:
                deferred_tasks.append(row)
                continue
            if week_domains.get(domain, 0) >= 2:
                deferred_tasks.append(row)
                continue
            if has_critical and urgency == 'MODERATE':
                deferred_tasks.append(row)
                continue

            # --- Add Task ---
            current_week['tasks'].append({
                'task_name':    row.get('task_name', ''),
                'domain':       domain,
                'urgency_tier': urgency,
                'difficulty_level': float(row.get('difficulty_level', 2.0)),
                'difficulty_order': float(row.get('difficulty_order', row.get('difficulty_level', 2.0))),
                'score':        round(float(row.get('score', 0.0)), 4),
            })
            current_week['minutes_used'] += task_mins
            week_domains[domain] = week_domains.get(domain, 0) + 1
            if urgency == 'CRITICAL':
                has_critical = True

        if not current_week['tasks']:
            # If no tasks could be scheduled (e.g. all tasks > MINUTES_PER_WEEK), prevent infinite loop
            # Just force the first deferred task in if we are stuck, or break if it's too big.
            if deferred_tasks and TASK_MINUTES.get(str(deferred_tasks[0].get('complexity', 'Medium')).strip().capitalize(), 120) > MINUTES_PER_WEEK:
                break # Task is impossible to schedule
            break

        weeks.append(current_week)
        tasks_to_schedule = deferred_tasks

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
    gap_row: dict | pd.Series,
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
            'user_id':            user_id,
            'created_date':       str(datetime.now().date()),
            'dream_role':         gap_row.get('dream_role', 'Unknown'),
            'career_gap':         float(gap_row.get('career_gap', 0.0)),
            'career_gap_tier':    gap_row.get('career_gap_tier', 'MODERATE'),
            'readiness_pct':      float(gap_row.get('readiness_pct', 0.0)),
            'total_weeks':        0,
            'roadmap_weeks':      [],
            'roadmap_health':     0.0,
            'domain_gaps':        domain_gaps,
            'summary': {
                'total_weeks': 0,
                'total_tasks': 0,
                'health_score': 0.0,
                'health_ok': False,
                'first_week_domains': [],
                'next_milestone': {
                    'description': 'No remaining role-matched tasks found.',
                },
            },
        }

    # Attach task complexity from catalog
    recs = recommendations.copy()
    recs['_task_key'] = recs['task_name'].apply(_normalize_task_name)
    recs = recs.drop_duplicates('_task_key')
    if task_data is not None and 'complexity' not in recs.columns:
        cmap = task_data.set_index('task_name')['complexity'].to_dict() if 'complexity' in task_data.columns else {}
        recs['complexity'] = recs['task_name'].map(cmap).fillna('Medium')
        dmap = task_data.set_index('task_name')['difficulty_level'].to_dict()
        recs['difficulty_level'] = recs['task_name'].map(dmap).fillna(2.0).astype(float)

    # Step 1: urgency tiering
    recs = _assign_urgency(recs, domain_gaps)
    sort_cols = [c for c in ['urgency_order', 'domain_priority',
                             'difficulty_order', 'difficulty_level', 'score']
                 if c in recs.columns]
    ascending = [True, True, True, True, False][:len(sort_cols)]
    recs = recs.sort_values(sort_cols, ascending=ascending)

    # Step 2: difficulty progression constraint
    recs = _enforce_difficulty_progression(recs)

    if len(recs) == 0:
        weeks = []
    else:
        # Step 3: week-by-week scheduling
        weeks = _schedule_weeks(recs)

    # Step 4: health score
    health = _health_score(weeks, domain_gaps)

    first_task = weeks[0]['tasks'][0] if weeks and weeks[0]['tasks'] else None

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
            'next_milestone': {
                'description': (
                    f"Complete {first_task['task_name']}"
                    if first_task else 'No valid difficulty-progressive tasks found.'
                ),
            },
        },
    }


# ─────────────────────────────────────────────────────────────────────────── #
#  Full Pipeline                                                              #
# ─────────────────────────────────────────────────────────────────────────── #

def _synthesize_role_domain_candidates(
    task_lookup: pd.DataFrame,
    domains: dict,
    domain_gaps: dict,
    top_k: int = 50,
) -> pd.DataFrame:
    """
    Build a role-specific, role-filtered candidate task pool directly from the
    task catalog, scored using Problem 2's authoritative mastery-vs-requirement
    gap instead of Problem 3's submission-count proxy.

    Args:
        task_lookup  : full task catalog DataFrame (from DataLoader)
        domains      : {domain: (required_mastery, weight)} from ROLE_REQUIREMENTS
        domain_gaps  : {domain: {raw_gap, weighted_gap, tier, ...}} from Problem 2
        top_k        : maximum candidates to return

    Returns:
        DataFrame with columns [task_name, domain, score, difficulty_level,
                                 complexity, domain_priority]
    """
    if task_lookup is None or task_lookup.empty:
        return pd.DataFrame()

    # Map the raw catalog domain tags to canonical domain names
    catalog = task_lookup.copy()
    catalog['domain'] = catalog['domain'].apply(hashtag_to_domain)

    # Only keep tasks belonging to the role's required domains
    role_domains = list(domains.keys())
    catalog = catalog[catalog['domain'].isin(role_domains)].copy()

    if catalog.empty:
        return pd.DataFrame()

    # Domain priority (lower index = higher priority in the role)
    domain_priority = {d: i for i, d in enumerate(role_domains)}

    # Score using authoritative P2 raw_gap × domain weight
    def _score(row):
        dom  = row['domain']
        gap  = domain_gaps.get(dom, {}).get('raw_gap', 0.0)
        weight = domains.get(dom, (0.5, 0.1))[1]
        # F16 fix: popularity boost capped at 0.1× to prevent a viral but irrelevant
        # task from outranking a critical skill-gap task. Without the cap, a popular
        # task scores up to 0.90 vs a critical-gap task at 0.05 (gap×weight).
        # With cap: popular boost ≤ 0.10, gap signal = up to 0.60 — gap always wins.
        popularity = float(row.get('real_attempts', 0))
        pop_boost  = 0.10 * popularity / (popularity + 1000)
        return round(gap * weight + pop_boost, 4)

    catalog['score'] = catalog.apply(_score, axis=1)
    catalog['domain_priority'] = catalog['domain'].map(domain_priority).fillna(99).astype(int)

    # Ensure required columns exist
    for col, default in [('difficulty_level', 2.0), ('complexity', 'Medium')]:
        if col not in catalog.columns:
            catalog[col] = default

    return (
        catalog
        .sort_values(['domain_priority', 'score'], ascending=[True, False])
        .head(top_k)
        [['task_name', 'domain', 'score', 'difficulty_level', 'complexity', 'domain_priority']]
        .reset_index(drop=True)
    )


def generate_career_roadmaps(
    career_gap_df: pd.DataFrame,
    pairs: pd.DataFrame,
    task_data: pd.DataFrame = None,
    top_k: int = 20,
) -> list:
    """
    Generate roadmaps for all users in career_gap_df.

    For users with a recognised dream role, candidates are built directly from
    the task catalog filtered to the role's required domains and scored using the
    authoritative Problem 2 mastery gap — NOT Problem 3's user-activity-scoped
    pairs (which are role-blind and pollute the roadmap with off-domain tasks).

    Users with an unrecognised role fall back to Problem 3's pairs so no edge
    case is broken.

    Args:
        career_gap_df : output of Problem 2
        pairs         : scored pairs from Problem 3 (fallback only)
        task_data     : task catalog
        top_k         : tasks to consider per user for scheduling

    Returns:
        list of roadmap dicts
    """
    logger.info(f'Generating roadmaps for {len(career_gap_df):,} users ...')
    roadmaps = []

    # Build a fallback lookup from Problem 3 pairs (for unrecognised roles)
    score_col   = 'final_score' if 'final_score' in pairs.columns else 'rule_score'
    pair_groups = {uid: grp for uid, grp in pairs.groupby('user_id', sort=False)}
    rec_cols    = ['task_name', 'domain', score_col]
    for optional_col in ['difficulty_level', 'difficulty_order', 'domain_priority', 'complexity']:
        if optional_col in pairs.columns:
            rec_cols.append(optional_col)

    for idx, (_, row) in enumerate(career_gap_df.iterrows()):
        uid        = row['user_id']
        dream_role = row.get('dream_role', '')
        try:
            dg_raw = row.get('domain_gaps_json', '{}')
            try:
                domain_gaps = json.loads(dg_raw) if isinstance(dg_raw, str) else (dg_raw or {})
            except Exception:
                domain_gaps = {}

            if dream_role in config.ROLE_REQUIREMENTS:
                # ── Role-aware path (correct) ─────────────────────────── #
                role_domains = config.ROLE_REQUIREMENTS[dream_role]
                recs = _synthesize_role_domain_candidates(
                    task_data, role_domains, domain_gaps, top_k=top_k * 3
                )
                if recs.empty:
                    # Graceful fallback: no catalog tasks found for this role
                    user_pairs = pair_groups.get(uid)
                    if user_pairs is None or len(user_pairs) == 0:
                        continue
                    recs = (
                        user_pairs.nlargest(top_k, score_col)[rec_cols]
                        .rename(columns={score_col: 'score'})
                    )
            else:
                # ── Fallback for unrecognised roles (old behaviour) ───── #
                user_pairs = pair_groups.get(uid)
                if user_pairs is None or len(user_pairs) == 0:
                    continue
                recs = (
                    user_pairs.nlargest(top_k, score_col)[rec_cols]
                    .rename(columns={score_col: 'score'})
                )

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
#  Failure Adaptation                                                         #
# ─────────────────────────────────────────────────────────────────────────── #

class FailureAdapter:
    """
    Tracks per-user task failures and adapts the roadmap accordingly.

    Rules (spec):
      3 failures → insert bridge task (difficulty - 1) before failed task
      5 failures → remove task entirely, mark domain as downgraded
    """

    def __init__(self):
        self.failure_counts:  dict = {}   # {user_id: {task_name: count}}
        self.degraded_domains: dict = {}  # {user_id: set of domain strings}
        self.action_log:      list = []

    def _log(self, message: str):
        entry = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}"
        self.action_log.append(entry)
        logger.info(entry)

    def record_failure(self, user_id: str, task_name: str, roadmap: dict) -> dict:
        """
        Record one failure for a task and adapt roadmap if threshold is hit.

        Args:
            user_id   : user identifier
            task_name : name of the failed task
            roadmap   : full roadmap dict returned by build_roadmap_for_user()

        Returns:
            Modified roadmap dict.
        """
        if user_id not in self.failure_counts:
            self.failure_counts[user_id] = {}
        self.failure_counts[user_id][task_name] = (
            self.failure_counts[user_id].get(task_name, 0) + 1
        )
        count = self.failure_counts[user_id][task_name]

        # Locate the task inside roadmap_weeks
        task_week = None
        task_idx  = None
        task_obj  = None
        for week in roadmap.get('roadmap_weeks', []):
            for i, t in enumerate(week['tasks']):
                if t['task_name'] == task_name:
                    task_week = week
                    task_idx  = i
                    task_obj  = t
                    break
            if task_week is not None:
                break

        if task_obj is None:
            self._log(f"Task '{task_name}' not found in roadmap for {user_id}")
            return roadmap

        domain     = task_obj['domain']
        difficulty = int(task_obj.get('difficulty_level', 2))

        if count == 3:
            bridge = {
                'task_name':        f'[Bridge] {domain.upper()} Foundations',
                'domain':           domain,
                'urgency_tier':     'BRIDGE',
                'difficulty_level': max(1, difficulty - 1),
                'difficulty_order': max(1, difficulty - 1),
                'score':            0.0,
                'is_bridge':        True,
            }
            task_week['tasks'].insert(task_idx, bridge)
            self._log(
                f"Bridge task inserted before '{task_name}' for {user_id} "
                f"after 3 failures (domain={domain}, difficulty={max(1, difficulty - 1)})"
            )

        elif count >= 5:
            task_week['tasks'].remove(task_obj)
            if not task_week['tasks']:
                roadmap['roadmap_weeks'].remove(task_week)

            if user_id not in self.degraded_domains:
                self.degraded_domains[user_id] = set()
            self.degraded_domains[user_id].add(domain)

            self._log(
                f"Task '{task_name}' removed for {user_id} after 5 failures. "
                f"Domain '{domain}' marked as downgraded."
            )

        return roadmap

    def get_status(self, user_id: str, task_name: str) -> dict:
        """Return failure count and latest action for a task."""
        count = self.failure_counts.get(user_id, {}).get(task_name, 0)
        return {
            'user_id':       user_id,
            'task_name':     task_name,
            'failure_count': count,
            'action_taken':  (
                'task_removed'    if count >= 5
                else 'bridge_inserted' if count >= 3
                else 'none'
            ),
            'log': [e for e in self.action_log if task_name in e and user_id in e],
        }

    def is_domain_degraded(self, user_id: str, domain: str) -> bool:
        """Check whether a domain has been downgraded for a user."""
        return domain in self.degraded_domains.get(user_id, set())

# ─────────────────────────────────────────────────────────────────────────── #
#  Revision Triggers                                                          #
# ─────────────────────────────────────────────────────────────────────────── #

class RoadmapRevisionEngine:
    """
    Event-driven roadmap revision triggers.

    Triggers (spec):
      - Inactivity    : ≥ 14 days no submission → shorten roadmap
      - Mastery surge : domain mastery delta ≥ 0.20 → skip ahead in that domain
      - Role change   : dream role updated → full regeneration required
      - Scheduled     : weekly refresh → rebuild from updated ranked list
    """

    def __init__(self):
        self.version:    int  = 1
        self.change_log: list = []

    def _log(self, message: str):
        entry = f"[v{self.version}] [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}"
        self.change_log.append(entry)
        logger.info(entry)

    def _increment_version(self):
        self.version += 1

    # ------------------------------------------------------------------ #

    def handle_inactivity(self, roadmap: dict, days_inactive: int) -> dict:
        """
        Triggered when a user has not submitted for ≥ 14 days.

        Action:
          - Remove the last 3 tasks from the roadmap
          - Prepend one easy re-engagement task to Week 1
        """
        if days_inactive < 14:
            return roadmap

        roadmap = _deep_copy_roadmap(roadmap)
        weeks   = roadmap.get('roadmap_weeks', [])

        # Remove last 3 tasks working backwards through weeks
        removed = 0
        for week in reversed(weeks):
            while week['tasks'] and removed < 3:
                week['tasks'].pop()
                removed += 1
            if removed == 3:
                break

        # Drop empty weeks
        roadmap['roadmap_weeks'] = [w for w in weeks if w['tasks']]

        # Prepend easy re-engagement task to Week 1
        if roadmap['roadmap_weeks']:
            first_week   = roadmap['roadmap_weeks'][0]
            first_domain = first_week['tasks'][0]['domain'] if first_week['tasks'] else 'general'
            reengagement = {
                'task_name':        f'[Re-engagement] {first_domain.upper()} Refresher',
                'domain':           first_domain,
                'urgency_tier':     'REENGAGEMENT',
                'difficulty_level': 1,
                'difficulty_order': 1,
                'score':            0.0,
                'is_bridge':        False,
            }
            first_week['tasks'].insert(0, reengagement)

        roadmap['total_weeks'] = len(roadmap['roadmap_weeks'])
        self._log(
            f"Inactivity trigger fired for {roadmap['user_id']} "
            f"({days_inactive} days). Removed {removed} tasks, added re-engagement task."
        )
        self._increment_version()
        return roadmap

    # ------------------------------------------------------------------ #

    def handle_mastery_surge(
        self,
        roadmap: dict,
        domain: str,
        mastery_increase: float,
    ) -> dict:
        """
        Triggered when a user's mastery in a domain increases by ≥ 0.20
        within a 7-day window (after Problem 1 recomputes features).

        Action:
          - Remove all tasks in that domain where difficulty_level ≤
            the scaled new mastery level (mastery 0–1 → difficulty 1–4)
        """
        if mastery_increase < 0.20:
            return roadmap

        roadmap        = _deep_copy_roadmap(roadmap)
        threshold_diff = max(1, round(mastery_increase * 4))
        removed_count  = 0

        for week in roadmap.get('roadmap_weeks', []):
            before = len(week['tasks'])
            week['tasks'] = [
                t for t in week['tasks']
                if not (
                    t['domain'] == domain
                    and int(t.get('difficulty_level', 2)) <= threshold_diff
                )
            ]
            removed_count += before - len(week['tasks'])

        # Drop empty weeks and re-number
        non_empty = [w for w in roadmap['roadmap_weeks'] if w['tasks']]
        for i, w in enumerate(non_empty, start=1):
            w['week'] = i
        roadmap['roadmap_weeks'] = non_empty
        roadmap['total_weeks']   = len(non_empty)

        self._log(
            f"Mastery surge in '{domain}' for {roadmap['user_id']} "
            f"(+{mastery_increase:.2f}). Removed {removed_count} tasks "
            f"at difficulty ≤ {threshold_diff}."
        )
        self._increment_version()
        return roadmap

    # ------------------------------------------------------------------ #

    def handle_role_change(self, roadmap: dict, new_role: str) -> None:
        """
        Triggered when a user updates their dream role.

        Action:
          - Returns None — signals to the caller that a full roadmap
            regeneration is required. The caller must rebuild from scratch
            using the new role.
        """
        self._log(
            f"Role change for {roadmap['user_id']}: "
            f"'{roadmap.get('dream_role')}' → '{new_role}'. "
            f"Full regeneration required."
        )
        self._increment_version()
        return None

    # ------------------------------------------------------------------ #

    def handle_scheduled_refresh(
        self,
        roadmap: dict,
        fresh_recs: pd.DataFrame,
        gap_row: dict | pd.Series,
        task_data: pd.DataFrame = None,
        top_k: int = 20,
    ) -> dict:
        """
        Triggered every 7 days (scheduled cron).

        Action:
          - Rebuild roadmap from scratch using the fresh real-time recommendations
            and gap data. Preserves user_id and dream_role.
        """
        user_id   = roadmap['user_id']
        score_col = 'final_score' if 'final_score' in fresh_recs.columns else 'rule_score'
        rec_cols  = ['task_name', 'domain', score_col]
        for col in ['difficulty_level', 'difficulty_order', 'domain_priority', 'complexity']:
            if col in fresh_recs.columns:
                rec_cols.append(col)

        if len(fresh_recs) == 0:
            self._log(f"Scheduled refresh skipped for {user_id}: no fresh recommendations found.")
            return roadmap

        recs = (
            fresh_recs.nlargest(top_k, score_col)[rec_cols]
            .rename(columns={score_col: 'score'})
        )

        new_roadmap = build_roadmap_for_user(user_id, gap_row, recs, task_data)

        self._log(
            f"Scheduled refresh completed for {user_id}. "
            f"New roadmap: {new_roadmap['total_weeks']} weeks, "
            f"health={new_roadmap['roadmap_health']}."
        )
        self._increment_version()
        return new_roadmap

    # ------------------------------------------------------------------ #

    def get_log(self) -> list:
        """Return the full change log for this engine instance."""
        return self.change_log


# ─────────────────────────────────────────────────────────────────────────── #
#  Internal Helper                                                            #
# ─────────────────────────────────────────────────────────────────────────── #

def _deep_copy_roadmap(roadmap: dict) -> dict:
    """
    Return a deep copy of a roadmap dict so mutations don't affect
    the original. Uses JSON round-trip for safety.
    """
    return json.loads(json.dumps(roadmap, default=str))

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
