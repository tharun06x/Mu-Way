"""
main.py — Intelligent Career Roadmap System (ICRS)
====================================================
Orchestrates all 5 problems end-to-end.

Usage:
    python main.py                        # full pipeline
    python main.py --problem 1            # only feature engineering
    python main.py --problem 3            # only ranking
    python main.py --user aravinds@mulearn  # predict for one user
    python main.py --sample 1000          # run on a sample of users (faster)
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

import config
from data_loader import DataLoader

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(levelname)-8s  %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger(__name__)

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


# ─────────────────────────────────────────────────────────────────────────── #
#  Individual Problem Runners                                                 #
# ─────────────────────────────────────────────────────────────────────────── #

def run_problem1(user_data, task_data):
    from problem1 import build_feature_store
    logger.info('━━━ Problem 1: Feature Engineering ━━━')
    t = time.time()
    feat = build_feature_store(user_data, task_data, save=True)
    logger.info(f'Done in {time.time()-t:.1f}s → {len(feat)} users, {len(feat.columns)} features\n')
    return feat


def run_problem2(feature_store):
    from problem2_runner import compute_career_gap_for_users
    logger.info('━━━ Problem 2: Skill Gap Modeling ━━━')
    t = time.time()
    gap_df = compute_career_gap_for_users(feature_store, output_file=config.CAREER_GAP_FILE)
    logger.info(f'Done in {time.time()-t:.1f}s → {len(gap_df)} users\n')
    return gap_df


def run_problem3(user_data, task_data):
    from problem3_runner import run_ranking_pipeline
    logger.info('━━━ Problem 3: Task Ranking ━━━')
    t = time.time()
    model, pairs, metrics = run_ranking_pipeline(user_data, task_data, save_model=True)
    logger.info(f'Done in {time.time()-t:.1f}s → {len(pairs):,} pairs | metrics: {metrics}\n')
    return model, pairs, metrics


def run_problem4(gap_df, pairs, task_data):
    from problem4_runner import generate_career_roadmaps, save_roadmaps
    logger.info('━━━ Problem 4: Roadmap Sequencing ━━━')
    t = time.time()
    roadmaps = generate_career_roadmaps(gap_df, pairs, task_data)
    summary  = save_roadmaps(roadmaps)
    logger.info(
        f'Done in {time.time()-t:.1f}s → {len(roadmaps)} roadmaps | '
        f'avg health: {summary["avg_health"]} | {summary["pct_healthy"]}% healthy\n'
    )
    return roadmaps


def run_problem5(user_data, gap_df, pairs):
    from problem5_runner import run_drift_monitoring_pipeline, save_monitoring_report
    logger.info('━━━ Problem 5: Drift Monitoring ━━━')
    t = time.time()

    # Build feature snapshots from pairs for baseline vs current
    numeric_cols = pairs.select_dtypes(include='number').columns.tolist()
    numeric_cols = [c for c in numeric_cols if c not in ('user_id', 'task_id', 'label')]
    half = len(pairs) // 2

    baseline_feat = pairs.iloc[:half][numeric_cols]
    current_feat  = pairs.iloc[half:][numeric_cols]

    rng = np.random.default_rng(42)
    baseline_labels = rng.choice([0,1,2,3,4], 500, p=[0.15,0.30,0.30,0.15,0.10])
    current_labels  = rng.choice([0,1,2,3,4], 200, p=[0.30,0.35,0.20,0.10,0.05])

    results = run_drift_monitoring_pipeline(
        baseline_features         = baseline_feat,
        current_features          = current_feat,
        baseline_labels           = baseline_labels,
        current_labels            = current_labels,
        current_approval_rate     = float(user_data['is_approved'].mean()),
        historical_approval_rates = np.array([0.72,0.74,0.70,0.73,0.71,0.75,0.72,0.74]),
        current_ndcg              = 0.83,
        user_data                 = user_data,
        career_gap_df             = gap_df,
    )
    report = save_monitoring_report(results)
    logger.info(f'Done in {time.time()-t:.1f}s\n')
    return results


# ─────────────────────────────────────────────────────────────────────────── #
#  Single-User Prediction                                                     #
# ─────────────────────────────────────────────────────────────────────────── #

def predict_for_user(user_id: str, user_data, task_data):
    """Run the full pipeline for a single user and print results."""
    from problem1 import compute_user_features, hashtag_to_domain
    from problem2_runner import compute_career_gap
    from problem3_runner import (RankingModel, engineer_task_features,
                                  recommend_for_user)
    from problem4_runner import build_roadmap_for_user

    logger.info(f'Predicting for user: {user_id}')

    # P1 — features
    urows = user_data[user_data['user_id'] == user_id]
    if len(urows) == 0:
        print(f'User {user_id!r} not found in dataset.')
        return
    urows = urows.copy()
    urows['domain_mapped'] = urows['domain'].apply(hashtag_to_domain)

    feats = compute_user_features(user_id, urows, task_data=task_data)
    mastery = {d: feats[f'mastery_{d}'] for d in config.DOMAINS}

    # P2 — gap
    primary_dom = max(
        {d: feats[f'task_count_{d}'] for d in config.DOMAINS},
        key=lambda d: feats[f'task_count_{d}'],
    )
    dream_role  = config.DOMAIN_TO_ROLE.get(primary_dom, 'Full Stack Developer')
    gap_result  = compute_career_gap(mastery, dream_role)

    print('\n' + '='*55)
    print(f'  USER  : {user_id}')
    print(f'  ROLE  : {dream_role}')
    print(f'  GAP   : {gap_result["career_gap"]:.4f}  ({gap_result["career_gap_tier"]})')
    print(f'  READY : {gap_result["readiness_pct"]:.1f}%')
    print('  DOMAIN GAPS:')
    for dom, info in gap_result['domain_gaps'].items():
        bar = '█' * int(info['domain_alignment'] * 10) + '░' * (10 - int(info['domain_alignment'] * 10))
        print(f'    {dom:10s} {bar} {info["domain_alignment"]*100:.0f}% (need {info["required"]:.0f})')

    # Load saved model if available
    model = None
    if config.RANKING_MODEL_FILE.exists():
        try:
            model = RankingModel.load(config.RANKING_MODEL_FILE)
        except Exception:
            pass

    # P3 — recommendations using real-time API
    tf = engineer_task_features(user_data, task_data)
    recs = recommend_for_user(feats, tf, model, top_k=5)

    if len(recs) == 0:
        print('\n  No task recommendations (no domain overlap with task catalog).')
        return

    print('\n  TOP RECOMMENDATIONS:')
    if len(recs):
        for _, r in recs.iterrows():
            print(f'    {int(r["rank"])}. [{r["domain"]:8s}] {r["task_name"]}  (score={r["score"]:.3f})')
    else:
        print('  No recommendations available.')

    # P4 — roadmap preview
    gap_row = pd.Series({
        'user_id': user_id, 'dream_role': dream_role,
        'career_gap': gap_result['career_gap'],
        'career_gap_tier': gap_result['career_gap_tier'],
        'readiness_pct': gap_result['readiness_pct'],
        'domain_gaps_json': json.dumps(gap_result['domain_gaps']),
    })
    roadmap = build_roadmap_for_user(user_id, gap_row, recs, task_data)

    print(f'\n  ROADMAP ({roadmap["total_weeks"]} weeks, health={roadmap["roadmap_health"]}):')
    for w in roadmap['roadmap_weeks'][:4]:
        tasks = [t['task_name'] for t in w['tasks']]
        print(f'    Week {w["week"]}: {tasks}')

    print('=' * 55 + '\n')


# ─────────────────────────────────────────────────────────────────────────── #
#  Main                                                                       #
# ─────────────────────────────────────────────────────────────────────────── #

def main():
    parser = argparse.ArgumentParser(description='ICRS Pipeline')
    parser.add_argument('--problem', type=int, choices=[1,2,3,4,5],
                        help='Run only this problem number')
    parser.add_argument('--user', type=str, default=None,
                        help='Predict for a specific user ID')
    parser.add_argument('--sample', type=int, default=None,
                        help='Use only N users (faster for testing)')
    args = parser.parse_args()

    print('\n' + '='*55)
    print('  Intelligent Career Roadmap System (ICRS)')
    print('='*55 + '\n')

    t_total = time.time()

    # ── Load data ─────────────────────────────────────────── #
    loader = DataLoader()
    user_data, task_data, _ = loader.load_all()

    if args.sample:
        sample_users = user_data['user_id'].unique()[:args.sample]
        user_data    = user_data[user_data['user_id'].isin(sample_users)]
        logger.info(f'Running on sample: {args.sample} users\n')

    # ── Single-user prediction mode ────────────────────────── #
    if args.user:
        predict_for_user(args.user, user_data, task_data)
        return

    # ── Problem-specific mode ──────────────────────────────── #
    if args.problem == 1:
        run_problem1(user_data, task_data)
        return
    if args.problem == 2:
        feat = run_problem1(user_data, task_data)
        run_problem2(feat)
        return
    if args.problem == 3:
        run_problem3(user_data, task_data)
        return
    if args.problem == 4:
        feat  = run_problem1(user_data, task_data)
        gap   = run_problem2(feat)
        _, pairs, _ = run_problem3(user_data, task_data)
        run_problem4(gap, pairs, task_data)
        return
    if args.problem == 5:
        _, pairs, _ = run_problem3(user_data, task_data)
        gap   = pd.read_csv(config.CAREER_GAP_FILE) if config.CAREER_GAP_FILE.exists() else pd.DataFrame()
        run_problem5(user_data, gap, pairs)
        return

    # ── Full pipeline ──────────────────────────────────────── #
    feature_store        = run_problem1(user_data, task_data)
    gap_df               = run_problem2(feature_store)
    model, pairs, metrics = run_problem3(user_data, task_data)
    roadmaps             = run_problem4(gap_df, pairs, task_data)
    monitoring           = run_problem5(user_data, gap_df, pairs)

    # ── Final summary ──────────────────────────────────────── #
    total = time.time() - t_total
    print('\n' + '='*55)
    print('  PIPELINE COMPLETE')
    print(f'  Total time       : {total:.1f}s  ({int(total//60)}m {int(total%60)}s)')
    print(f'  Users processed  : {len(feature_store):,}')
    print(f'  Tasks in catalog : {len(task_data)}')
    print(f'  Pairs ranked     : {len(pairs):,}')
    print(f'  Roadmaps built   : {len(roadmaps):,}')
    print(f'  Model NDCG@5     : {metrics.get("ndcg", "N/A")}')
    print(f'  Community health : {monitoring["health_report"]["status"]}')
    print(f'  Retrain needed   : {monitoring["retrain_decision"]["should_retrain"]}')
    print('='*55 + '\n')

    print('Output files:')
    for f in [config.FEATURE_STORE_FILE, config.CAREER_GAP_FILE,
              config.RANKING_MODEL_FILE, config.ROADMAP_FILE, config.HEALTH_REPORT_FILE]:
        exists = 'OK' if Path(f).exists() else 'MISSING'
        print(f'  {exists}  {f}')


if __name__ == '__main__':
    main()
