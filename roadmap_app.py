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
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd

import config
from data_loader import DataLoader
from problem1 import compute_user_features, hashtag_to_domain
from problem2_runner import compute_career_gap
from problem3_runner import (
    RankingModel, engineer_user_features, engineer_task_features,
    create_domain_matched_pairs, engineer_advanced_features,
    generate_labels, compute_rule_score, recommend,
)
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

    bar = f'{bar_color}{"█" * filled}{C.DIM}{"░" * empty}{C.RESET}'
    pct = f'{value*100:5.1f}%'
    return f'{bar} {pct}  {dim(label)}'


TIER_COLOR = {
    'CRITICAL': C.RED,
    'MODERATE': C.YELLOW,
    'MARGINAL': C.BLUE,
    'MET':      C.GREEN,
}

WEEK_ICONS = ['①', '②', '③', '④', '⑤', '⑥', '⑦', '⑧',
              '⑨', '⑩', '⑪', '⑫', '⑬', '⑭', '⑮', '⑯']

DOMAIN_ICONS = {
    'web':     '🌐', 'ai':      '🤖', 'ds':      '📊',
    'dsa':     '🧩', 'devops':  '⚙️', 'cybersec':'🔐',
    'android': '📱', 'general': '📚',
}


# ──────────────────────────────────────────────────────────────────────── #
#  Spinner                                                                  #
# ──────────────────────────────────────────────────────────────────────── #

def spinner_task(label: str, func, *args, **kwargs):
    """Run func with a terminal spinner; return result."""
    frames = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
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
    sys.stdout.write(f'\r  {C.GREEN}✓{C.RESET}  {label}          \n')
    sys.stdout.flush()
    return result_holder[0]


# ──────────────────────────────────────────────────────────────────────── #
#  Input helpers                                                            #
# ──────────────────────────────────────────────────────────────────────── #

def prompt(label: str, default: str = '') -> str:
    hint = f' [{dim(default)}]' if default else ''
    val  = input(f'  {cyan("▸")} {bold(label)}{hint}: ').strip()
    return val or default


def select_role() -> str:
    roles = list(config.ROLE_REQUIREMENTS.keys())
    print(f'\n  {bold("Available Dream Roles:")}')
    for i, r in enumerate(roles, 1):
        print(f'    {dim(str(i)+".")} {r}')
    print()

    while True:
        choice = input(f'  {cyan("▸")} {bold("Enter role name or number")}: ').strip()
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(roles):
                return roles[idx]
        else:
            # fuzzy match
            for r in roles:
                if choice.lower() in r.lower():
                    return r
        print(f'  {red("✗")} Not recognised — try again.')


# ──────────────────────────────────────────────────────────────────────── #
#  Core: build everything for one user                                      #
# ──────────────────────────────────────────────────────────────────────── #

def _load_data():
    loader = DataLoader()
    return loader.load_all()


def generate_roadmap(muid: str, name: str, role: str,
                     user_data: pd.DataFrame, task_data: pd.DataFrame) -> dict:
    """
    Full pipeline for one user:
      P1 → features
      P2 → career gap
      P3 → recommendations
      P4 → roadmap
    Returns a rich result dict.
    """
    # ── P1 ─────────────────────────────────────────────── #
    rows = user_data[user_data['user_id'] == muid].copy()
    known_user = len(rows) > 0

    if known_user:
        rows['domain_mapped'] = rows['domain'].apply(hashtag_to_domain)
        features = compute_user_features(muid, rows, task_data=task_data)
    else:
        # Cold-start: build empty feature vector
        features = {
            'user_id': muid,
            'total_submissions': 0, 'experience_level': 1,
            'global_approval_rate': 0.5, 'engagement_score': 0.0,
            'optimal_difficulty': 1.5, 'days_since_last_submission': 999,
            'is_cold_start': 1, 'approved_count': 0,
        }
        for d in config.DOMAINS:
            features[f'mastery_{d}']       = 0.0
            features[f'approval_conf_{d}'] = 0.5
            features[f'task_count_{d}']    = 0
            features[f'interest_{d}']      = 0.0

    # ── P2 ─────────────────────────────────────────────── #
    mastery = {d: features[f'mastery_{d}'] for d in config.DOMAINS}
    gap     = compute_career_gap(mastery, role)

    # ── P3 ─────────────────────────────────────────────── #
    if known_user:
        rows2 = rows.copy()
    else:
        # Synthesise minimal frame for cold-start
        rows2 = pd.DataFrame([{
            'user_id': muid, 'domain': 'general', 'domain_mapped': 'general',
            'task_name': '__cold__', 'task_id': -1,
            'submission_date': pd.Timestamp.now(), 'is_approved': 0,
            'difficulty_level': 1,
        }])

    uf    = engineer_user_features(rows2)
    tf    = engineer_task_features(rows2, task_data)
    pairs = create_domain_matched_pairs(uf, tf)

    if len(pairs) == 0:
        # Fall back: give ALL tasks in the role's required domains
        required_domains = list(config.ROLE_REQUIREMENTS[role].keys())
        tf_sub  = task_data[task_data['domain'].apply(hashtag_to_domain).isin(required_domains)].copy()
        tf_sub['domain'] = tf_sub['domain'].apply(hashtag_to_domain)
        if len(tf_sub) == 0:
            tf_sub = task_data.copy()
            tf_sub['domain'] = tf_sub['domain'].apply(hashtag_to_domain)
        # Create simple pairs without user features
        pairs = tf_sub[['task_name', 'domain']].copy()
        pairs.insert(0, 'user_id', muid)
        pairs['interest_score']   = 0.3
        pairs['gap_score']        = 0.7
        pairs['submission_count'] = 0
        pairs['mastery']          = 0.0
        pairs['approval_rate']    = 0.5
        pairs['community_approval'] = 0.5
        pairs['difficulty']       = 0.5
        if 'difficulty_level' not in pairs.columns:
            diff_map = task_data.set_index('task_name')['difficulty_level'].to_dict()
            pairs['difficulty_level'] = pairs['task_name'].map(diff_map).fillna(2).astype(int)

    if len(pairs) > 0 and 'difficulty_suitability' not in pairs.columns:
        pairs = engineer_advanced_features(pairs)
    if len(pairs) > 0 and 'label' not in pairs.columns:
        pairs = generate_labels(pairs)
    if len(pairs) > 0 and 'rule_score' not in pairs.columns:
        pairs = compute_rule_score(pairs)

    # Load saved ML model if available
    model = None
    if config.RANKING_MODEL_FILE.exists():
        try:
            model = RankingModel.load(config.RANKING_MODEL_FILE)
        except Exception:
            pass

    recs = recommend(pairs, model, muid, top_k=20) if len(pairs) else pd.DataFrame()

    # ── P4 ─────────────────────────────────────────────── #
    gap_row = pd.Series({
        'user_id': muid, 'dream_role': role,
        'career_gap':      gap['career_gap'],
        'career_gap_tier': gap['career_gap_tier'],
        'readiness_pct':   gap['readiness_pct'],
        'domain_gaps_json': gap['domain_gaps_json'],
    })

    # Attach complexity to recs for scheduling
    if len(recs) and 'complexity' not in recs.columns:
        c_map = task_data.set_index('task_name')['difficulty_level'].to_dict() \
                if 'difficulty_level' in task_data.columns else {}
        recs['difficulty_level'] = recs['task_name'].map(c_map).fillna(2).astype(int)
        recs['complexity'] = recs['difficulty_level'].map({1: 'Low', 2: 'Medium', 3: 'High', 4: 'High'})

    roadmap = build_roadmap_for_user(muid, gap_row, recs, task_data)

    return {
        'muid':       muid,
        'name':       name,
        'role':       role,
        'known_user': known_user,
        'features':   features,
        'gap':        gap,
        'recs':       recs,
        'roadmap':    roadmap,
    }


# ──────────────────────────────────────────────────────────────────────── #
#  Display                                                                  #
# ──────────────────────────────────────────────────────────────────────── #

def display_roadmap(result: dict):
    gap     = result['gap']
    roadmap = result['roadmap']
    recs    = result['recs']
    feats   = result['features']

    os.system('clear' if os.name == 'posix' else 'cls')

    # ── HERO ─────────────────────────────────────────────────── #
    print(f'\n{C.CYAN}{"═"*WIDTH}{C.RESET}')
    print(f'{C.BOLD}{C.CYAN}  🎯  INTELLIGENT CAREER ROADMAP SYSTEM{C.RESET}')
    print(f'{C.CYAN}{"═"*WIDTH}{C.RESET}')

    print(f'\n  {bold("Name")}  :  {cyan(result["name"])}')
    print(f'  {bold("MUID")}  :  {dim(result["muid"])}')
    print(f'  {bold("Role")}  :  {magenta(result["role"])}')

    status = (
        green('◉ Known user') if result['known_user']
        else yellow('◎ New user  (cold-start defaults applied)')
    )
    print(f'  {bold("Status")} :  {status}')

    if result['known_user']:
        total = feats.get('total_submissions', 0)
        days  = feats.get('days_since_last_submission', 0)
        eng   = feats.get('engagement_score', 0)
        print(f'\n  {dim("Submissions:")} {total}   '
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
    header('TOP 5 TASK RECOMMENDATIONS')
    print()
    if len(recs):
        for _, r in recs.head(5).iterrows():
            icon  = DOMAIN_ICONS.get(str(r.get('domain', 'general')), '●')
            score = float(r.get('score', 0))
            rtype = str(r.get('reason', 'Rule-based'))
            label = dim('ML') if 'ML' in rtype else dim('Rule')
            print(f'  {int(r["rank"])}. {icon} {bold(r["task_name"])}')
            print(f'     {dim("domain:")} {r["domain"]:10s}  '
                  f'{dim("score:")} {score:.3f}  {label}')
            print()
    else:
        print(f'  {yellow("No recommendations available.")}')

    # ── WEEK-BY-WEEK ROADMAP ──────────────────────────────────── #
    header(f'WEEK-BY-WEEK ROADMAP  ({roadmap["total_weeks"]} weeks)')

    health = roadmap.get('roadmap_health', 0)
    health_color = C.GREEN if health >= 0.8 else C.YELLOW if health >= 0.5 else C.RED
    print(f'\n  Roadmap health score : {health_color}{C.BOLD}{health:.2f}{C.RESET}  '
          f'{"✓ Healthy" if health >= 0.8 else "⚠ Needs improvement"}')
    print(f'  Estimated duration   : {roadmap["total_weeks"]} weeks  '
          f'{dim("(3 hrs/week)")}\n')

    weeks = roadmap.get('roadmap_weeks', [])
    if not weeks:
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
                  + dim(f'({w["hours_used"]} hrs)'))

            for task in tier_tasks:
                t_icon = DOMAIN_ICONS.get(task['domain'], '●')
                tc     = TIER_COLOR.get(task.get('urgency_tier', 'MODERATE'), C.WHITE)
                tag    = f'{tc}▸{C.RESET}'
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
    print(f'{C.BOLD}{C.CYAN}  🎯  INTELLIGENT CAREER ROADMAP SYSTEM{C.RESET}')
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

    print(f'\n  {green("✓")} Got it, {bold(name)}! Generating your roadmap for '
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
    export = input(f'  {cyan("▸")} Export roadmap to JSON? (y/N): ').strip().lower()
    if export == 'y':
        out_path = f'output/roadmap_{muid.split("@")[0]}.json'
        os.makedirs('output', exist_ok=True)
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
        print(f'\n  {green("✓")} Saved → {bold(out_path)}\n')

    # ── Try another? ───────────────────────────────────────────── #
    again = input(f'  {cyan("▸")} Generate for another user? (y/N): ').strip().lower()
    if again == 'y':
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
