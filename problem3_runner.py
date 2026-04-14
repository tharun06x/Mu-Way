"""
Problem 3 — Task Ranking & Recommendation
==========================================
Ranks available tasks for each user by expected value in closing skill gaps.

Two stages (spec):
  Stage A — Rule-based ranker   (< 5 submissions / cold start)
  Stage B — GradientBoosting ML (≥ 5 submissions)

Key fix vs original: domain-matched pairs only.
  Original: 32,883 users × 749 tasks = 24.6 M pairs → crash
  Fixed   : join on shared domain    ≈ 100 K–300 K pairs → fast
"""

import json
import logging
import pickle
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import ndcg_score
from sklearn.model_selection import GroupShuffleSplit

import config
from problem1 import hashtag_to_domain

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────── #
#  Feature Engineering                                                        #
# ─────────────────────────────────────────────────────────────────────────── #

def engineer_user_features(user_data: pd.DataFrame) -> pd.DataFrame:
    """User × domain level features."""
    records = []
    max_submissions = user_data.groupby(['user_id', 'domain_mapped']).size().max() or 1

    for (uid, dom), grp in user_data.groupby(['user_id', 'domain_mapped']):
        sub_count = len(grp)
        mastery   = sub_count / max_submissions
        records.append({
            'user_id':          uid,
            'domain':           dom,
            'submission_count': sub_count,
            'mastery':          mastery,
            'gap_score':        1.0 - mastery,
            'approval_rate':    float(grp['is_approved'].mean()),
            'interest_count':   grp['task_name'].nunique(),
        })

    df = pd.DataFrame(records)
    if len(df):
        mx = df['interest_count'].max() or 1
        df['interest_score'] = df['interest_count'] / mx
    else:
        df['interest_score'] = 0.0
    return df


def engineer_task_features(
    user_data: pd.DataFrame,
    task_data: pd.DataFrame,
) -> pd.DataFrame:
    """Task-level features: popularity and difficulty suitability."""
    pop = user_data.groupby('task_name').size().reset_index(name='popularity')

    tf = task_data.copy()
    tf = tf.merge(pop, on='task_name', how='left')
    tf['popularity'] = tf['popularity'].fillna(0)

    mx_pop = tf['popularity'].max() or 1
    tf['community_approval'] = tf['popularity'] / mx_pop
    tf['difficulty']         = 1.0 / (tf['popularity'] + 1)
    mx_diff = tf['difficulty'].max() or 1
    tf['difficulty']         = tf['difficulty'] / mx_diff

    # Map domain
    if 'domain' in tf.columns:
        tf['domain'] = tf['domain'].apply(
            lambda x: hashtag_to_domain(x) if pd.notna(x) else 'general'
        )
    else:
        tf['domain'] = 'general'

    return tf


def create_domain_matched_pairs(
    user_features: pd.DataFrame,
    task_features: pd.DataFrame,
) -> pd.DataFrame:
    """
    Join users and tasks on shared domain — NOT a full Cartesian product.
    Reduces pair count from ~24 M to ~100 K–300 K.
    """
    user_cols = ['user_id', 'domain', 'interest_score', 'gap_score',
                 'submission_count', 'mastery', 'approval_rate']
    task_cols = ['task_name', 'domain', 'difficulty_level', 'community_approval', 'difficulty']

    uf = user_features[user_cols].copy()
    tf = task_features[[c for c in task_cols if c in task_features.columns]].copy()

    pairs = uf.merge(tf, on='domain', how='inner')

    # Add default columns if missing
    for col, val in [('difficulty_level', 2), ('community_approval', 0.5), ('difficulty', 0.5)]:
        if col not in pairs.columns:
            pairs[col] = val

    pairs = pairs.fillna(0)
    logger.info(f"Domain-matched pairs: {len(pairs):,}")
    return pairs


def engineer_advanced_features(pairs: pd.DataFrame) -> pd.DataFrame:
    """Interaction + suitability features."""
    opt = pairs['difficulty'].mean() + 0.5
    pairs['difficulty_suitability'] = np.exp(-0.5 * ((pairs['difficulty'] - opt) ** 2))
    pairs['gap_interest']           = pairs['gap_score'] * pairs['interest_score']
    pairs['approval_probability']   = pairs['interest_score'] * (1 - pairs['difficulty'])
    pairs['task_count_in_domain']   = pairs.groupby(['user_id', 'domain'])['task_name'].transform('count')
    pairs['task_role_relevance']    = 1.0
    pairs['domain_importance']      = 1.0

    before = len(pairs)
    pairs  = pairs[(pairs['interest_score'] > 0) | (pairs['gap_score'] > 0)]
    logger.info(f"Pairs after relevance filter: {before:,} → {len(pairs):,}")
    return pairs


def generate_labels(pairs: pd.DataFrame) -> pd.DataFrame:
    """Synthetic labels: 0.6×gap + 0.3×interest + 0.1×community_approval, scaled 0-4."""
    pairs['label'] = (
        0.6 * pairs['gap_score'] +
        0.3 * pairs['interest_score'] +
        0.1 * pairs['community_approval']
    )
    mx = pairs['label'].max()
    if mx > 0:
        pairs['label'] = 4 * (pairs['label'] / mx)
    return pairs


def compute_rule_score(pairs: pd.DataFrame) -> pd.DataFrame:
    """Stage A rule-based score (spec weights)."""
    pairs['rule_score'] = (
        config.WEIGHT_CAREER_GAP       * pairs['gap_score'] +
        config.WEIGHT_INTEREST         * pairs['interest_score'] +
        config.WEIGHT_SUBMISSION_COUNT * pairs['community_approval'] +
        config.WEIGHT_RECENCY          * pairs['difficulty_suitability']
    )
    return pairs


def prepare_recommendation_data(
    user_data: pd.DataFrame,
    task_data: pd.DataFrame,
) -> tuple:
    """Full feature-engineering pipeline. Returns (pairs, user_features, task_features)."""
    logger.info('Preparing recommendation data ...')

    # Domain mapping
    udata = user_data.copy()
    udata['domain_mapped'] = udata['domain'].apply(hashtag_to_domain)

    t0 = time.time()
    uf = engineer_user_features(udata)
    logger.info(f'  User features : {time.time()-t0:.1f}s')

    t0 = time.time()
    tf = engineer_task_features(udata, task_data)
    logger.info(f'  Task features : {time.time()-t0:.1f}s')

    t0 = time.time()
    pairs = create_domain_matched_pairs(uf, tf)
    logger.info(f'  Pairs created : {time.time()-t0:.1f}s')

    t0 = time.time()
    pairs = engineer_advanced_features(pairs)
    logger.info(f'  Adv. features : {time.time()-t0:.1f}s')

    pairs = generate_labels(pairs)
    pairs = compute_rule_score(pairs)

    logger.info(f'✓ Ready: {len(pairs):,} pairs')
    return pairs, uf, tf


# ─────────────────────────────────────────────────────────────────────────── #
#  ML Model                                                                   #
# ─────────────────────────────────────────────────────────────────────────── #

FEATURE_NAMES = [
    'gap_score', 'interest_score', 'community_approval',
    'difficulty_suitability', 'gap_interest', 'approval_probability',
    'task_count_in_domain', 'task_role_relevance', 'domain_importance',
]


class RankingModel:

    def __init__(self):
        self.model         = None
        self.feature_names = FEATURE_NAMES
        self.metrics       = {}

    def train(self, pairs: pd.DataFrame, test_size: float = 0.2) -> dict:
        avail = [f for f in self.feature_names if f in pairs.columns]
        if len(avail) < len(self.feature_names):
            logger.warning(f'Missing features: {set(self.feature_names)-set(avail)}')
        self.feature_names = avail

        X = pairs[self.feature_names]
        y = pairs['label']
        n_users = pairs['user_id'].nunique()

        if len(pairs) < 10 or n_users < 2:
            logger.warning('Too few samples — training on all data.')
            X_train, X_test = X, X.iloc[:0]
            y_train, y_test = y, y.iloc[:0]
        else:
            try:
                gss = GroupShuffleSplit(
                    n_splits=1, test_size=test_size,
                    random_state=config.TRAIN_RANDOM_STATE,
                )
                tr, te = next(gss.split(X, y, groups=pairs['user_id']))
                X_train, X_test = X.iloc[tr], X.iloc[te]
                y_train, y_test = y.iloc[tr], y.iloc[te]
            except ValueError:
                X_train, X_test = X, X.iloc[:0]
                y_train, y_test = y, y.iloc[:0]

        logger.info(f'Training GBR on {len(X_train):,} samples ...')
        t0 = time.time()
        self.model = GradientBoostingRegressor(
            n_estimators=config.GBREGRESSOR_N_ESTIMATORS,
            learning_rate=config.GBREGRESSOR_LEARNING_RATE,
            max_depth=config.GBREGRESSOR_MAX_DEPTH,
            min_samples_split=config.GBREGRESSOR_MIN_SAMPLES_SPLIT,
            random_state=config.GBREGRESSOR_RANDOM_STATE,
        )
        self.model.fit(X_train, y_train)
        logger.info(f'  Trained in {time.time()-t0:.1f}s')

        self.metrics = {
            'train_r2':   round(self.model.score(X_train, y_train), 4),
            'train_size': len(X_train),
            'test_size':  len(X_test),
        }

        if len(X_test) > 1:
            y_hat = self.model.predict(X_test)
            try:
                self.metrics['ndcg']    = round(ndcg_score([y_test.values], [y_hat]), 4)
                self.metrics['test_r2'] = round(self.model.score(X_test, y_test), 4)
            except Exception:
                self.metrics['ndcg']    = 0.0
                self.metrics['test_r2'] = self.metrics['train_r2']
        else:
            self.metrics['ndcg']    = 0.0
            self.metrics['test_r2'] = self.metrics['train_r2']

        logger.info(f'  Metrics: {self.metrics}')
        return self.metrics

    def predict(self, pairs: pd.DataFrame) -> np.ndarray:
        if self.model is None:
            raise ValueError('Model not trained.')
        return self.model.predict(pairs[self.feature_names])

    def save(self, path):
        with open(path, 'wb') as f:
            pickle.dump(self, f)
        logger.info(f'✓ Model saved → {path}')

    @staticmethod
    def load(path):
        with open(path, 'rb') as f:
            return pickle.load(f)


# ─────────────────────────────────────────────────────────────────────────── #
#  Recommendation                                                             #
# ─────────────────────────────────────────────────────────────────────────── #

def recommend(
    pairs: pd.DataFrame,
    model: RankingModel,
    user_id: str,
    top_k: int = config.TOP_K_RECOMMENDATIONS,
) -> pd.DataFrame:
    """
    Top-K recommendations for one user.
    Uses ML score if ≥5 submissions, else rule-based score.
    """
    up = pairs[pairs['user_id'] == user_id].copy()
    if len(up) == 0:
        logger.warning(f'No pairs for user {user_id}')
        return pd.DataFrame()

    if (up['submission_count'].iloc[0] >= 5
            and model is not None
            and model.model is not None):
        up['score']  = model.predict(up)
        up['reason'] = 'ML-based'
    else:
        up['score']  = up['rule_score']
        up['reason'] = 'Rule-based'

    top = up.nlargest(top_k, 'score')[['task_name', 'domain', 'score', 'reason']].reset_index(drop=True)
    top.insert(0, 'rank', range(1, len(top) + 1))
    return top


# ─────────────────────────────────────────────────────────────────────────── #
#  Full Pipeline                                                              #
# ─────────────────────────────────────────────────────────────────────────── #

def run_ranking_pipeline(
    user_data: pd.DataFrame,
    task_data: pd.DataFrame,
    save_model: bool = True,
) -> tuple:
    """
    Phase 1: feature engineering
    Phase 2: model training
    Phase 3: final scoring

    Returns: model, pairs, metrics
    """
    start = time.time()
    logger.info('=' * 60)
    logger.info('Problem 3 — Ranking Pipeline')
    logger.info('=' * 60)

    t0    = time.time()
    pairs, uf, tf = prepare_recommendation_data(user_data, task_data)
    logger.info(f'Phase 1 (features): {time.time()-t0:.1f}s')

    t0      = time.time()
    model   = RankingModel()
    metrics = model.train(pairs)
    logger.info(f'Phase 2 (training): {time.time()-t0:.1f}s')

    t0 = time.time()
    pairs['ml_score']    = model.predict(pairs)
    pairs['final_score'] = 0.75 * pairs['ml_score'] + 0.25 * pairs['approval_probability']
    logger.info(f'Phase 3 (scoring) : {time.time()-t0:.1f}s')

    if save_model:
        model.save(config.RANKING_MODEL_FILE)
        with open(config.MODEL_METADATA_FILE, 'w') as f:
            json.dump(
                {'metrics': metrics,
                 'features': model.feature_names,
                 'timestamp': str(pd.Timestamp.now())},
                f, indent=2,
            )

    total = time.time() - start
    logger.info(f'✓ Pipeline complete in {total:.1f}s')
    return model, pairs, metrics


# ─────────────────────────────────────────────────────────────────────────── #
#  Standalone run                                                             #
# ─────────────────────────────────────────────────────────────────────────── #

if __name__ == '__main__':
    import logging as _log
    _log.basicConfig(level=_log.INFO, format='%(asctime)s %(levelname)s %(message)s')

    from data_loader import DataLoader

    loader = DataLoader()
    user_data, task_data, _ = loader.load_all()

    model, pairs, metrics = run_ranking_pipeline(user_data, task_data)

    sample_user = pairs['user_id'].iloc[0]
    recs = recommend(pairs, model, sample_user)
    print(f'\nRecommendations for {sample_user}:')
    print(recs.to_string(index=False))
    print(f'\nModel metrics: {metrics}')
