"""
roadmap_app.py — Interactive Career Roadmap Generator
======================================================
Enter your MUID, name, and dream role → get a full personalised roadmap.

Usage:
    python roadmap_app.py
    python roadmap_app.py --muid aravinds@mulearn --name "Arun" --role "AI Engineer"
"""

import argparse
import json
import os
import sys
import time
import warnings
from pathlib import Path
warnings.filterwarnings('ignore')

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import numpy as np
import pandas as pd

import config
from data_loader import DataLoader
from problem1 import compute_user_features, hashtag_to_domain
from problem2_runner import compute_career_gap
from problem3_runner import RankingModel, engineer_task_features, recommend_for_user
from problem4_runner import build_roadmap_for_user


# ──────────────────────────────────────────────────────────────────────── #
#  Terminal colour helpers                                                  #
# ──────────────────────────────────────────────────────────────────────── #

class C:
    RESET  = '\033[0m'
    BOLD   = '\033[1m'
    DIM    = '\033[2m'
    CYAN   = '\033[96m'
    GREEN  = '\033[92m'
    YELLOW = '\033[93m'
    RED    = '\033[91m'
    BLUE   = '\033[94m'
    MAGENTA= '\033[95m'
    WHITE  = '\033[97m'
    BG_DARK= '\033[40m'

def bold(s):   return f'{C.BOLD}{s}{C.RESET}'
def cyan(s):   return f'{C.CYAN}{s}{C.RESET}'
def green(s):  return f'{C.GREEN}{s}{C.RESET}'
def yellow(s): return f'{C.YELLOW}{s}{C.RESET}'
def red(s):    return f'{C.RED}{s}{C.RESET}'
def blue(s):   return f'{C.BLUE}{s}{C.RESET}'
def dim(s):    return f'{C.DIM}{s}{C.RESET}'
def magenta(s):return f'{C.MAGENTA}{s}{C.RESET}'


# ──────────────────────────────────────────────────────────────────────── #
#  Display helpers                                                          #
# ──────────────────────────────────────────────────────────────────────── #

WIDTH = 62

def divider(char='─', color=C.DIM):
    print(f'{color}{char * WIDTH}{C.RESET}')

def header(text, color=C.CYAN):
    pad = (WIDTH - len(text) - 2) // 2
    print(f'\n{color}{"─"*pad} {C.BOLD}{text}{C.RESET}{color} {"─"*(WIDTH-pad-len(text)-2)}{C.RESET}')

def progress_bar(value: float, width: int = 20, label: str = '') -> str:
    """Render a coloured progress bar for a 0-1 value."""
    filled = int(round(value * width))
    empty  = width - filled

    if value >= 0.70:   bar_color = C.GREEN
    elif value >= 0.40: bar_color = C.YELLOW
    else:               bar_color = C.RED

    bar = f'{bar_color}{"#" * filled}{C.DIM}{"-" * empty}{C.RESET}'
    pct = f'{value*100:5.1f}%'
    return f'{bar} {pct}  {dim(label)}'


TIER_COLOR = {
    'CRITICAL': C.RED,
    'MODERATE': C.YELLOW,
    'MARGINAL': C.BLUE,
    'MET':      C.GREEN,
}

WEEK_ICONS = [str(i) for i in range(1, 17)]

DOMAIN_ICONS = {
    'web': 'WEB', 'ai': 'AI', 'ds': 'DS',
    'dsa': 'DSA', 'devops': 'DEVOPS', 'cybersec': 'SEC',
    'android': 'AND', 'general': 'GEN',
}

DIFFICULTY_LABELS = {
    1: 'Beginner',
    2: 'Intermediate',
    3: 'Advanced',
    4: 'Expert',
}

RELATED_DOMAINS = {
    'ai': ['ds', 'dsa', 'web'],
    'ds': ['ai', 'dsa', 'web'],
    'web': ['dsa', 'devops', 'android'],
    'dsa': ['web', 'ai', 'ds'],
    'devops': ['web', 'cybersec'],
    'cybersec': ['devops', 'web', 'dsa'],
    'android': ['web', 'dsa'],
    'general': ['web', 'dsa', 'ds'],
}


# ──────────────────────────────────────────────────────────────────────── #
#  Spinner                                                                  #
# ──────────────────────────────────────────────────────────────────────── #

def spinner_task(label: str, func, *args, **kwargs):
    """Run func with a terminal spinner; return result."""
    frames = ['|', '/', '-', '\\']
    result_holder = [None]
    done_flag     = [False]

    import threading

    def _run():
        result_holder[0] = func(*args, **kwargs)
        done_flag[0] = True

    t = threading.Thread(target=_run)
    t.start()

    i = 0
    while not done_flag[0]:
        frame = frames[i % len(frames)]
        sys.stdout.write(f'\r  {C.CYAN}{frame}{C.RESET}  {label} ...')
        sys.stdout.flush()
        time.sleep(0.08)
        i += 1

    t.join()
    sys.stdout.write(f'\r  {C.GREEN}OK{C.RESET}  {label}          \n')
    sys.stdout.flush()
    return result_holder[0]


# ──────────────────────────────────────────────────────────────────────── #
#  Input helpers                                                            #
# ──────────────────────────────────────────────────────────────────────── #

def prompt(label: str, default: str = '') -> str:
    hint = f' [{dim(default)}]' if default else ''
    val  = input(f'  {cyan("->")} {bold(label)}{hint}: ').strip()
    return val or default


def select_role() -> str:
    roles = list(config.ROLE_REQUIREMENTS.keys())
    print(f'\n  {bold("Available Dream Roles:")}')
    for i, r in enumerate(roles, 1):
        print(f'    {dim(str(i)+".")} {r}')
    print()

    while True:
        choice = input(f'  {cyan("->")} {bold("Enter role name or number")}: ').strip()
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(roles):
                return roles[idx]
        else:
            # fuzzy match
            for r in roles:
                if choice.lower() in r.lower():
                    return r
        print(f'  {red("X")} Not recognised — try again.')


# ──────────────────────────────────────────────────────────────────────── #
#  Core: build everything for one user                                      #
# ──────────────────────────────────────────────────────────────────────── #

def _load_data():
    loader = DataLoader()
    return loader.load_all()


def _normalize_task_name(value) -> str:
    """Normalize task names so completed-task filtering is reliable."""
    if pd.isna(value):
        return ''
    return ' '.join(str(value).strip().lower().split())


def _roadmap_task_limit(gap: dict, rec_count: int) -> int:
    """Pick a person-sized next plan instead of filling every possible week."""
    if rec_count <= 0:
        return 0
    readiness = float(gap.get('readiness_pct', 0.0))
    if readiness >= 90:
        limit = 4
    elif readiness >= 75:
        limit = 6
    elif readiness >= 55:
        limit = 10
    else:
        limit = 16
    return min(rec_count, limit)


def _rank_and_number_recs(recs: pd.DataFrame) -> pd.DataFrame:
    if len(recs) == 0:
        return recs
    recs = recs.copy()
    recs = recs.drop_duplicates('_task_key' if '_task_key' in recs.columns else 'task_name')
    sort_cols = [c for c in ['difficulty_order', 'domain_priority', 'score'] if c in recs.columns]
    if sort_cols:
        ascending = [True, True, False][:len(sort_cols)]
        recs = recs.sort_values(sort_cols, ascending=ascending)
    recs = recs.reset_index(drop=True)
    if 'rank' in recs.columns:
        recs = recs.drop(columns=['rank'])
    recs.insert(0, 'rank', range(1, len(recs) + 1))
    return recs


def _build_additional_skill_recs(
    rows: pd.DataFrame,
    task_data: pd.DataFrame,
    done_tasks: set,
    role_domains: list,
    max_items: int = 8,
) -> pd.DataFrame:
    td = task_data.copy()
    td['domain_mapped'] = td['domain'].apply(hashtag_to_domain)
    td['_task_key'] = td['task_name'].apply(_normalize_task_name)

    interest_domains = []
    if len(rows) and 'domain_mapped' in rows.columns:
        interest_domains = rows['domain_mapped'].value_counts().index.tolist()

    related = []
    for dom in list(role_domains) + interest_domains:
        for rel in RELATED_DOMAINS.get(dom, []):
            if rel not in role_domains and rel not in related:
                related.append(rel)

    if not related:
        related = [d for d in config.DOMAINS if d not in role_domains]

    candidates = td[
        td['domain_mapped'].isin(related)
        & ~td['_task_key'].isin(done_tasks)
    ].copy()
    if len(candidates) == 0:
        return pd.DataFrame()

    candidates['_related_priority'] = candidates['domain_mapped'].apply(
        lambda d: related.index(d) if d in related else 99
    )
    candidates = candidates.sort_values(
        ['difficulty_level', '_related_priority', 'task_karma_value'],
        ascending=[True, True, False],
    )

    records = []
    for _, t in candidates.drop_duplicates('_task_key').head(max_items).iterrows():
        diff = int(t.get('difficulty_level', 2))
        records.append({
            'task_name': t['task_name'],
            'domain': t['domain_mapped'],
            'difficulty_level': diff,
            'difficulty_label': DIFFICULTY_LABELS.get(diff, 'Intermediate'),
            'score': 0.0,
            'reason': 'Related skill',
        })

    recs = pd.DataFrame(records)
    if len(recs):
        recs.insert(0, 'rank', range(1, len(recs) + 1))
    return recs


def generate_roadmap(muid: str, name: str, role: str,
                     user_data: pd.DataFrame, task_data: pd.DataFrame) -> dict:
    """
    Full pipeline for one user.

    Fixes applied:
      1. Exclude tasks the user has already done.
      2. Recommend only tasks in domains required by the target role
         (primary role domains first, general only as filler).
      3. Difficulty progression: start from just above the user's current
         level per domain and go harder.
    """
    # ── P1 — Features ─────────────────────────────────────── #
    rows = user_data[user_data['user_id'] == muid].copy()
    known_user = len(rows) > 0

    if known_user:
        rows['domain_mapped'] = rows['domain'].apply(hashtag_to_domain)
        features = compute_user_features(muid, rows, ref=pd.Timestamp.now())
    else:
        features = _cold_start_features(muid)

    # ── P2 — Career Gap ───────────────────────────────────── #
    mastery = {d: features[f'mastery_{d}'] for d in config.DOMAINS}
    gap      = compute_career_gap(mastery, role)

    # ── Build task pool for this role ─────────────────────── #
    role_reqs        = config.ROLE_REQUIREMENTS[role]
    all_role_domains = list(role_reqs.keys())          # includes general
    domain_priority  = {domain: idx for idx, domain in enumerate(all_role_domains)}
    
    # Inject maximum interest for all domains required by the target role
    # This forces the ML engine to generate pairs and score tasks for these domains
    for d in all_role_domains:
        features[f'interest_{d}'] = 1.0

    # Map every task to a canonical domain
    td = task_data.copy()
    td['domain_mapped'] = td['domain'].apply(hashtag_to_domain)
    td['_task_key'] = td['task_name'].apply(_normalize_task_name)

    # Keep only tasks relevant to this role
    role_tasks = td[td['domain_mapped'].isin(all_role_domains)].copy()
    if len(role_tasks) == 0:
        role_tasks = td.copy()    # last resort fallback

    # ── Fix 1: Exclude already-done tasks ─────────────────── #
    done_tasks: set = set()
    if known_user:
        done_tasks = {
            _normalize_task_name(task)
            for task in rows['task_name'].dropna().unique()
        }

    available = role_tasks[~role_tasks['_task_key'].isin(done_tasks)].copy()
    role_complete = known_user and len(role_tasks) > 0 and len(available) == 0

    # ── Fix 3: Difficulty progression per domain ──────────── #
    # Find the user's highest approved difficulty per domain
    domain_levels: dict = {}
    if known_user:
        approved = rows[rows['is_approved'] == 1].copy()
        approved['domain_mapped'] = approved['domain'].apply(hashtag_to_domain)
        if 'difficulty_level' in approved.columns:
            for dom, grp in approved.groupby('domain_mapped'):
                domain_levels[dom] = int(grp['difficulty_level'].max())

    def next_difficulty(domain: str) -> int:
        """One level above what user has already cleared (min 1, max 4)."""
        current = domain_levels.get(domain, 0)
        return max(1, min(current + 1, 4))

    # ── Fix 2: ML Recommendations (Real-Time API) ───────────── #
    tf = engineer_task_features(user_data, task_data)
    
    # Load ML model if available for warm users
    model = None
    if known_user and config.RANKING_MODEL_FILE.exists():
        try:
            model = RankingModel.load(config.RANKING_MODEL_FILE)
        except Exception:
            pass

    # Fetch all scored tasks for the user using the genuine ML engine
    raw_recs = recommend_for_user(features, tf, model, top_k=9999)
    if raw_recs.empty:
        raw_recs = pd.DataFrame(columns=['task_name', 'domain', 'score', 'reason'])

    raw_recs['_task_key'] = raw_recs['task_name'].apply(_normalize_task_name)
    
    # ── Fix 3: Filter & Sort for Roadmap ────────────────────── #
    # 1. Exclude already-done tasks
    available = raw_recs[~raw_recs['_task_key'].isin(done_tasks)].copy()
    
    # 2. Filter to role domains only
    available = available[available['domain'].isin(all_role_domains)].copy()
    role_complete = known_user and len(role_tasks) > 0 and len(available) == 0

    records = []
    if not available.empty:
        # Attach difficulty for sorting and rendering
        dmap = task_data.set_index('task_name')['difficulty_level'].to_dict()
        available['difficulty_level'] = available['task_name'].map(dmap).fillna(2.0).astype(float)
        
        def sort_key(row):
            dom  = row['domain']
            diff = float(row.get('difficulty_level', 2.0))
            next_diff = next_difficulty(dom)
            diff_score = diff if diff >= next_diff else diff + 10
            return diff_score

        available['difficulty_order'] = available.apply(sort_key, axis=1)
        available['domain_priority']  = available['domain'].map(domain_priority).fillna(99)
        
        # Apply ML Score Threshold
        available = available[available['score'] >= 0.05]

        # Apply Difficulty Floor
        available = available[available['difficulty_level'] >= available.apply(lambda r: next_difficulty(r['domain']), axis=1) - 1.0]
        
        # Sort by Domain Priority -> Difficulty Progression -> ML Score
        available = available.sort_values(
            ['domain_priority', 'difficulty_order', 'score'], 
            ascending=[True, True, False]
        )
        
        for _, t in available.iterrows():
            diff = float(t['difficulty_level'])
            records.append({
                'task_name':        t['task_name'],
                '_task_key':        t['_task_key'],
                'domain':           t['domain'],
                'difficulty_level': diff,
                'difficulty_order': t['difficulty_order'],
                'difficulty_label': DIFFICULTY_LABELS.get(int(diff), 'Intermediate'),
                'domain_priority':  t['domain_priority'],
                'gap_score':        max(0.0, role_reqs.get(t['domain'], (0.5, 0.1))[0] - mastery.get(t['domain'], 0.0)),
                'score':            round(t['score'], 4),
                'reason':           t['reason'],
                'complexity':      {1:'Low', 2:'Medium', 3:'High', 4:'High'}.get(int(diff), 'Medium'),
            })

    if not records:
        recs = pd.DataFrame()
    else:
        recs = pd.DataFrame(records)
        recs = _rank_and_number_recs(recs)

    additional_recs = pd.DataFrame()
    if role_complete:
        additional_recs = _build_additional_skill_recs(
            rows=rows,
            task_data=task_data,
            done_tasks=done_tasks,
            role_domains=all_role_domains,
        )

    roadmap_recs = recs.copy()
    if not role_complete and len(roadmap_recs):
        roadmap_limit = _roadmap_task_limit(gap, len(roadmap_recs))
        roadmap_recs = _rank_and_number_recs(roadmap_recs.head(roadmap_limit))
    elif role_complete:
        roadmap_recs = pd.DataFrame()

    # ── P4 — Roadmap ─────────────────────────────────────────── #
    gap_row = pd.Series({
        'user_id':          muid,
        'dream_role':       role,
        'career_gap':       gap['career_gap'],
        'career_gap_tier':  gap['career_gap_tier'],
        'readiness_pct':    gap['readiness_pct'],
        'domain_gaps_json': gap['domain_gaps_json'],
    })
    roadmap = build_roadmap_for_user(muid, gap_row, roadmap_recs, task_data)

    return {
        'muid':       muid,
        'name':       name,
        'role':       role,
        'known_user': known_user,
        'features':   features,
        'gap':        gap,
        'recs':       roadmap_recs,
        'all_recs':   recs,
        'additional_recs': additional_recs,
        'roadmap':    roadmap,
        'done_count': len(done_tasks),
        'role_complete': role_complete,
    }


def _cold_start_features(muid: str) -> dict:
    """Return all-zero feature vector for unknown users."""
    feat = {
        'user_id': muid, 'total_submissions': 0, 'experience_level': 1,
        'global_approval_rate': 0.5, 'engagement_score': 0.0,
        'optimal_difficulty': 1.5, 'days_since_last_submission': 999,
        'is_cold_start': 1, 'approved_count': 0,
    }
    for d in config.DOMAINS:
        feat[f'mastery_{d}']       = 0.0
        feat[f'approval_conf_{d}'] = 0.5
        feat[f'task_count_{d}']    = 0
        feat[f'interest_{d}']      = 0.0
    return feat


# ──────────────────────────────────────────────────────────────────────── #
#  Display                                                                  #
# ──────────────────────────────────────────────────────────────────────── #

def display_roadmap(result: dict):
    gap     = result['gap']
    roadmap = result['roadmap']
    recs    = result['recs']
    feats   = result['features']
    additional_recs = result.get('additional_recs', pd.DataFrame())
    role_complete = result.get('role_complete', False)

    os.system('clear' if os.name == 'posix' else 'cls')

    # ── HERO ─────────────────────────────────────────────────── #
    print(f'\n{C.CYAN}{"═"*WIDTH}{C.RESET}')
    print(f'{C.BOLD}{C.CYAN}    INTELLIGENT CAREER ROADMAP SYSTEM{C.RESET}')
    print(f'{C.CYAN}{"═"*WIDTH}{C.RESET}')

    print(f'\n  {bold("Name")}  :  {cyan(result["name"])}')
    print(f'  {bold("MUID")}  :  {dim(result["muid"])}')
    print(f'  {bold("Role")}  :  {magenta(result["role"])}')

    status = (
        green('Known user') if result['known_user']
        else yellow('New user  (cold-start defaults applied)')
    )
    print(f'  {bold("Status")} :  {status}')

    if result['known_user']:
        total = feats.get('total_submissions', 0)
        days  = feats.get('days_since_last_submission', 0)
        eng   = feats.get('engagement_score', 0)
        done  = result.get('done_count', 0)
        print(f'\n  {dim("Submissions:")} {total}   '
              f'{dim("Tasks completed:")} {done}   '
              f'{dim("Days since last:")} {days}   '
              f'{dim("Engagement:")} {eng:.2f}')

    # ── CAREER GAP ───────────────────────────────────────────── #
    header('CAREER READINESS')

    tier_color = TIER_COLOR.get(gap['career_gap_tier'], C.WHITE)
    tier_label = f'{tier_color}{C.BOLD}{gap["career_gap_tier"]}{C.RESET}'
    print(f'\n  Overall Readiness  {progress_bar(gap["alignment_score"], 24)}')
    cg_val = f'{gap["career_gap"]:.4f}'
    print(f'  Career Gap Score   {bold(cg_val)}  →  {tier_label}')
    rp1 = f'{gap["readiness_pct"]:.1f}%'
    print(f'  Alignment          {cyan(rp1)} toward {magenta(result["role"])}')

    # ── DOMAIN BREAKDOWN ─────────────────────────────────────── #
    header('DOMAIN SKILL GAPS')
    print()
    domain_gaps = json.loads(gap['domain_gaps_json'])

    for domain, info in sorted(domain_gaps.items(),
                                key=lambda x: x[1]['weighted_gap'], reverse=True):
        icon      = DOMAIN_ICONS.get(domain, '●')
        align     = info['domain_alignment']
        tier      = info['tier']
        tc        = TIER_COLOR.get(tier, C.WHITE)
        tier_tag  = f'{tc}[{tier:8s}]{C.RESET}'
        need_str  = f"need {info['required']:.0%}"
        bar       = progress_bar(align, 18, need_str)
        dom_label = bold(f'{domain:10s}')
        print(f'  {icon} {dom_label}  {tier_tag}  {bar}')

    # ── TOP RECOMMENDATIONS ───────────────────────────────────── #
    header('RECOMMENDED TASK PATH')
    print()
    if role_complete:
        print(f'  {green("All good.")} You have completed the available '
              f'{magenta(result["role"])} role tasks.')
        print(f'  {dim("Next:")} Explore related skills below.')
    elif len(recs):
        # B16 fix: floor to int so groupby produces clean Beginner/Intermediate/Advanced buckets
        recs = recs.copy()
        recs['_diff_int'] = recs['difficulty_level'].apply(lambda x: int(float(x)))
        for diff, group in recs.groupby('_diff_int', sort=True):
            diff = int(diff)
            domains = ', '.join(
                f'{DOMAIN_ICONS.get(str(dom), "GEN")} {dom}'
                for dom in group['domain'].drop_duplicates().head(4)
            )
            print(f'  {bold(DIFFICULTY_LABELS.get(diff, "Intermediate"))} '
                  f'{dim(f"(level {diff})")}  '
                  f'{len(group)} task(s)  {dim(domains)}')
    else:
        print(f'  {yellow("No recommendations available.")}')

    if role_complete and len(additional_recs):
        header('ADDITIONAL RELATED SKILLS')
        print()
        for _, r in additional_recs.iterrows():
            icon = DOMAIN_ICONS.get(str(r.get('domain', 'general')), 'GEN')
            diff = int(r.get('difficulty_level', 2))
            print(f'  {int(r["rank"])}. {icon} {bold(r["task_name"])}')
            print(f'     {dim("domain:")} {r["domain"]:10s}  '
                  f'{dim("level:")} {DIFFICULTY_LABELS.get(diff, "Intermediate")}')
        print()

    # ── WEEK-BY-WEEK ROADMAP ──────────────────────────────────── #
    header(f'WEEK-BY-WEEK ROADMAP  ({roadmap["total_weeks"]} weeks)')

    health = roadmap.get('roadmap_health', 0)
    health_color = C.GREEN if health >= 0.8 else C.YELLOW if health >= 0.5 else C.RED
    if role_complete:
        print(f'\n  Roadmap status       : {green("Complete")}')
        print(f'  Estimated duration   : 0 weeks  {dim("(no role tasks pending)")}\n')
    else:
        print(f'\n  Roadmap health score : {health_color}{C.BOLD}{health:.2f}{C.RESET}  '
              f'{"Healthy" if health >= 0.8 else "Needs improvement"}')
        print(f'  Estimated duration   : {roadmap["total_weeks"]} weeks  '
              f'{dim("(3 hrs/week)")}\n')

    weeks = roadmap.get('roadmap_weeks', [])
    if not weeks:
        if role_complete:
            print(f'  {green("No role roadmap needed right now.")}')
        else:
            print(f'  {yellow("Roadmap could not be generated (no matched tasks).")}')
    else:
        for w in weeks:
            icon = WEEK_ICONS[w['week'] - 1] if w['week'] <= len(WEEK_ICONS) else f'W{w["week"]}'
            tier_tasks = w.get('tasks', [])

            # Colour week header by its urgency
            tiers = [t.get('urgency_tier', 'MODERATE') for t in tier_tasks]
            week_color = (
                C.RED    if 'CRITICAL' in tiers else
                C.YELLOW if 'MODERATE' in tiers else
                C.BLUE
            )
            print(f'  {week_color}{C.BOLD}{icon} Week {w["week"]}{C.RESET}  '
                  + dim(f'({w.get("minutes_used", 0)} mins)'))

            for task in tier_tasks:
                t_icon = DOMAIN_ICONS.get(task['domain'], '●')
                tc     = TIER_COLOR.get(task.get('urgency_tier', 'MODERATE'), C.WHITE)
                tag    = f'{tc}->{C.RESET}'
                diff   = '★' * int(task.get('difficulty_level', 2)) + \
                         dim('☆' * (4 - int(task.get('difficulty_level', 2))))
                print(f'      {tag} {t_icon} {task["task_name"]}')
                print(f'         {dim("domain:")} {task["domain"]:10s}  '
                      f'{dim("diff:")} {diff}  '
                      f'{tc}{task.get("urgency_tier","")}{C.RESET}')
            print()

    # ── NEXT STEPS ────────────────────────────────────────────── #
    header('WHAT TO DO NOW')
    nxt = roadmap.get('summary', {}).get('next_milestone')
    if nxt:
        print(f'\n  Start with  →  {green(nxt.get("description", ""))}')
    if weeks:
        first_tasks = [t['task_name'] for t in weeks[0].get('tasks', [])]
        print(f'  Week 1 plan →  {", ".join(first_tasks[:3])}')
    rp0 = f'{gap["readiness_pct"]:.0f}%'
    print(f'\n  Keep going! You are {cyan(rp0)} ready '
          f'for {magenta(result["role"])}.\n')

    print(f'{C.CYAN}{"═"*WIDTH}{C.RESET}\n')


# ──────────────────────────────────────────────────────────────────────── #
#  Main                                                                     #
# ──────────────────────────────────────────────────────────────────────── #

def main():
    parser = argparse.ArgumentParser(description='ICRS Roadmap Generator')
    parser.add_argument('--muid', type=str, default=None)
    parser.add_argument('--name', type=str, default=None)
    parser.add_argument('--role', type=str, default=None)
    args = parser.parse_args()

    os.system('clear' if os.name == 'posix' else 'cls')

    print(f'\n{C.CYAN}{"═"*WIDTH}{C.RESET}')
    print(f'{C.BOLD}{C.CYAN}    INTELLIGENT CAREER ROADMAP SYSTEM{C.RESET}')
    print(f'{C.CYAN}  Powered by muLearn · ICRS v1.0{C.RESET}')
    print(f'{C.CYAN}{"═"*WIDTH}{C.RESET}\n')

    # ── Collect inputs ─────────────────────────────────────────── #
    muid = args.muid or prompt('Enter your MUID  (e.g. aravinds@mulearn)')
    if not muid:
        print(red('  MUID is required.'))
        sys.exit(1)

    name = args.name or prompt('Enter your name ', default=muid.split('@')[0].capitalize())
    role = args.role

    if not role:
        role = select_role()

    if role not in config.ROLE_REQUIREMENTS:
        # Try fuzzy
        for r in config.ROLE_REQUIREMENTS:
            if role.lower() in r.lower():
                role = r
                break
        else:
            print(red(f'  Role "{role}" not found.'))
            sys.exit(1)

    print(f'\n  {green("OK")} Got it, {bold(name)}! Generating your roadmap for '
          f'{magenta(role)} ...\n')

    # ── Load data ──────────────────────────────────────────────── #
    print(f'  {dim("Loading dataset ...")}')
    user_data, task_data, _ = spinner_task('Loading data', _load_data)

    # ── Generate ───────────────────────────────────────────────── #
    result = spinner_task(
        'Building your personalised roadmap',
        generate_roadmap,
        muid, name, role, user_data, task_data,
    )

    # ── Display ────────────────────────────────────────────────── #
    display_roadmap(result)

    # ── Ask to export ──────────────────────────────────────────── #
    export = input(f'  {cyan("->")} Export roadmap to JSON? (y/N): ').strip().lower()
    if export == 'y':
        # B17 fix: use Path to build a portable, absolute-safe output path
        out_dir  = Path(config.OUTPUT_DIR).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        safe_id  = result['muid'].split('@')[0].replace('/', '_')
        out_path = out_dir / f'roadmap_{safe_id}.json'
        export_data = {
            'muid':          result['muid'],
            'name':          result['name'],
            'role':          result['role'],
            'career_gap':    result['gap']['career_gap'],
            'readiness_pct': result['gap']['readiness_pct'],
            'career_gap_tier': result['gap']['career_gap_tier'],
            'domain_gaps':   result['gap']['domain_gaps'],
            'top_recommendations': result['recs'].head(10).to_dict(orient='records') if len(result['recs']) else [],
            'roadmap':       result['roadmap'],
        }
        with open(out_path, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        print(f'  {green("OK")} Saved -> {bold(out_path)}\n')

    # ── Try another? (unlimited retries) ──────────────────────────────── #
    while True:
        again = input(f'  {cyan("->")} Generate for another user? (y/N): ').strip().lower()
        if again != 'y':
            break
        print()
        muid2 = prompt('Enter MUID')
        name2 = prompt('Enter name', default=muid2.split('@')[0].capitalize())
        role2 = select_role()
        result2 = spinner_task(
            'Building roadmap',
            generate_roadmap,
            muid2, name2, role2, user_data, task_data,
        )
        display_roadmap(result2)


if __name__ == '__main__':
    main()
