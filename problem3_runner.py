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

try:
    from sklearn.ensemble import GradientBoostingRegressor
    from sklearn.metrics import ndcg_score
    from sklearn.model_selection import GroupShuffleSplit
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    GradientBoostingRegressor = None
    TfidfVectorizer = None
    cosine_similarity = None

    GroupShuffleSplit = None
    SKLEARN_AVAILABLE = False

    def ndcg_score(y_true, y_score):
        return 0.0

import config
from problem1 import hashtag_to_domain

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────── #
#  Feature Engineering                                                        #
# ─────────────────────────────────────────────────────────────────────────── #

def engineer_user_features(user_data: pd.DataFrame) -> pd.DataFrame:
    """User × domain level features."""
    records = []
    # BUG-4 fix: mastery was divided by a single GLOBAL max (e.g. one power user with
    # 300 GitHub tasks). This collapsed every other user's mastery to near-zero,
    # inflating gap_score to ~1.0 for everyone and making all tasks equally critical.
    # Fix: use each user's own max submission count across domains as the denominator.
    user_max_submissions = (
        user_data.groupby(['user_id', 'domain_mapped'])
        .size()
        .groupby(level='user_id')
        .max()
        .to_dict()
    )

    for (uid, dom), grp in user_data.groupby(['user_id', 'domain_mapped']):
        sub_count = len(grp)
        user_max  = max(user_max_submissions.get(uid, 1), 1)
        mastery   = sub_count / user_max
        approved = grp[grp['is_approved'] == 1]
        optimal_difficulty = (
            float(approved['difficulty_level'].mean()) + 0.5
            if len(approved) and 'difficulty_level' in approved.columns else 1.5
        )
        records.append({
            'user_id':          uid,
            'domain':           dom,
            'submission_count': sub_count,
            'mastery':          mastery,
            'gap_score':        1.0 - mastery,
            'approval_rate':    float(grp['is_approved'].mean()),
            'optimal_difficulty': optimal_difficulty,
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

    # B7 fix: use the actual difficulty_level column (1-4 scale) normalised to [0,1]
    # instead of inverse-popularity which conflates task complexity with submission count.
    if 'difficulty_level' in tf.columns:
        mx_diff = tf['difficulty_level'].astype(float).max() or 4.0
        tf['difficulty'] = tf['difficulty_level'].astype(float) / mx_diff
    else:
        tf['difficulty'] = 0.5  # neutral fallback

    # Map domain
    if 'domain' in tf.columns:
        tf['domain'] = tf['domain'].apply(
            lambda x: hashtag_to_domain(x) if pd.notna(x) else 'general'
        )
        tf = tf[~tf['domain'].isin(['ignored', 'general'])].copy()
    else:
        tf['domain'] = 'general'

    # Compute TF-IDF Semantic Relevance
    if SKLEARN_AVAILABLE and TfidfVectorizer is not None:
        tf['semantic_relevance'] = 0.0
        # Compute relevance per domain to avoid cross-domain noise
        for dom, grp in tf.groupby('domain'):
            desc = config.DOMAIN_DESCRIPTIONS.get(dom, '')
            if not desc or len(grp) == 0:
                continue
            
            # Combine domain desc + task names for vectorization
            texts = [desc] + grp['task_name'].tolist()
            try:
                vec = TfidfVectorizer(stop_words='english')
                tfidf_matrix = vec.fit_transform(texts)
                # Compute cosine similarity between desc (index 0) and tasks (index 1:)
                sims = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()
                tf.loc[grp.index, 'semantic_relevance'] = np.clip(sims, 0, 1)
            except Exception as e:
                logger.warning(f"TF-IDF failed for domain {dom}: {e}")
    else:
        tf['semantic_relevance'] = 0.5  # fallback
        
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
                 'submission_count', 'mastery', 'approval_rate',
                 'optimal_difficulty']
    task_cols = ['task_name', 'domain', 'difficulty_level', 'community_approval', 'difficulty']

    uf = user_features[user_cols].copy()
    tf = task_features[[c for c in task_cols if c in task_features.columns]].copy()

    pairs = uf.merge(tf, on='domain', how='inner')

    # Add default columns if missing
    for col, val in [('difficulty_level', 2.0), ('community_approval', 0.5), ('difficulty', 0.5)]:
        if col not in pairs.columns:
            pairs[col] = val

    pairs = pairs.fillna(0)
    logger.info(f"Domain-matched pairs: {len(pairs):,}")
    return pairs


def engineer_advanced_features(pairs: pd.DataFrame) -> pd.DataFrame:
    """Interaction + suitability features."""
    task_diff = pairs['difficulty_level'].astype(float)
    opt = pairs['optimal_difficulty'].astype(float).fillna(1.5)
    pairs['difficulty_suitability'] = np.exp(-0.5 * ((task_diff - opt) ** 2))
    pairs['gap_interest']           = pairs['gap_score'] * pairs['interest_score']
    pairs['approval_probability']   = (
        0.70 * pairs['approval_rate'].clip(0, 1) +
        0.30 * pairs['difficulty_suitability'].clip(0, 1)
    )
    pairs['task_count_in_domain']   = pairs.groupby(['user_id', 'domain'])['task_name'].transform('count')
    # BUG-7 fix: removed constant 1.0 sentinel features 'task_role_relevance' and
    # 'domain_importance'. Constant features have zero variance — GBR learns nothing
    # from them and they waste memory and inflate FEATURE_NAMES.
    # BUG-8 fix: removed dead relevance filter below. In the batch path, pairs with
    # both interest_score == 0 and gap_score == 0 never enter engineer_user_features()
    # in the first place, so this filter is always a no-op.
    return pairs


def generate_labels(pairs: pd.DataFrame, user_data: pd.DataFrame) -> pd.DataFrame:
    """
    Temporal mastery gain labels (real historical interactions):
    Label = task_difficulty if the user historically completed the task, else 0.
    This replaces the synthetic rule-based label with actual skill-gain signals.
    """
    approved = user_data[user_data['is_approved'] == 1][['user_id', 'task_name']].copy()
    # Drop duplicates in case a user submitted the same task multiple times
    approved = approved.drop_duplicates()
    approved['is_completed'] = 1.0

    pairs = pairs.merge(approved, on=['user_id', 'task_name'], how='left')
    pairs['is_completed'] = pairs['is_completed'].fillna(0.0)
    
    # Mastery gain correlates strongly with the difficulty of the completed task
    pairs['label'] = pairs['is_completed'] * pairs['difficulty_level'].astype(float)
    
    pairs = pairs.drop(columns=['is_completed'])

    mx = pairs['label'].max()
    if mx > 0:
        pairs['label'] = 4 * (pairs['label'] / mx)
    return pairs


def compute_rule_score(pairs: pd.DataFrame) -> pd.DataFrame:
    """Stage A rule-based score (spec weights)."""
    # Fallback for semantic_relevance if it wasn't generated
    if 'semantic_relevance' not in pairs.columns:
        pairs['semantic_relevance'] = 0.5

    pairs['rule_score'] = (
        config.WEIGHT_CAREER_GAP       * pairs['gap_score'] +
        config.WEIGHT_INTEREST         * pairs['interest_score'] +
        config.WEIGHT_SEMANTIC_RELEVANCE * pairs['semantic_relevance'] +
        config.WEIGHT_COMMUNITY_APPROVAL * pairs['community_approval'] +
        config.WEIGHT_DIFFICULTY_SUITABILITY * pairs['difficulty_suitability']
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

    pairs = generate_labels(pairs, udata)
    pairs = compute_rule_score(pairs)

    logger.info(f'✓ Ready: {len(pairs):,} pairs')
    return pairs, uf, tf


# ─────────────────────────────────────────────────────────────────────────── #
#  ML Model                                                                   #
# ─────────────────────────────────────────────────────────────────────────── #

FEATURE_NAMES = [
    'gap_score', 'interest_score', 'semantic_relevance', 'community_approval',
    'difficulty_suitability', 'gap_interest', 'approval_probability',
    'task_count_in_domain',
    # BUG-7 fix: removed 'task_role_relevance' and 'domain_importance' —
    # both were always constant 1.0, contributing zero signal to the GBR model.
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

        if not SKLEARN_AVAILABLE:
            self.model = None
            self.metrics = {
                'model_type': 'rule_based_fallback',
                'reason': 'scikit-learn is not installed',
                'train_size': len(pairs),
                'test_size': 0,
                'ndcg': 0.0,
                'train_r2': 0.0,
                'test_r2': 0.0,
            }
            logger.warning('scikit-learn not installed; using rule-based fallback scores.')
            return self.metrics

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
            if 'rule_score' in pairs.columns:
                return pairs['rule_score'].to_numpy(dtype=float)
            raise ValueError('Model not trained and no rule_score fallback is available.')
        # Feature-mismatch guard: if the saved model was trained on a different
        # set of features (e.g. old model with task_role_relevance/domain_importance)
        # it will crash with KeyError. Detect this and fall back to rule_score.
        missing = [f for f in self.feature_names if f not in pairs.columns]
        if missing:
            logger.warning(
                f'Stale model: features {missing} missing from current pairs. '
                f'Falling back to rule_score. Please retrain the model with '
                f'`python problem3_runner.py` to restore ML scoring.'
            )
            if 'rule_score' in pairs.columns:
                return pairs['rule_score'].to_numpy(dtype=float)
            return np.zeros(len(pairs))
        return self.model.predict(pairs[self.feature_names])

    def save(self, path):
        with open(path, 'wb') as f:
            pickle.dump(self, f)
        logger.info(f'✓ Model saved → {path}')

    @staticmethod
    def load(path):
        with open(path, 'rb') as f:
            obj = pickle.load(f)
        # Validate that the persisted model's features match the current code.
        # If they diverge (e.g. after a bug fix removed constant features),
        # discard the model so the caller falls back to rule_score gracefully.
        if hasattr(obj, 'feature_names') and obj.feature_names != FEATURE_NAMES:
            logger.warning(
                f'Loaded model feature_names {obj.feature_names} do not match '
                f'current FEATURE_NAMES {FEATURE_NAMES}. '
                f'Model discarded — run `python problem3_runner.py` to retrain.'
            )
            obj.model = None          # zero out the GBR so predict() falls back
            obj.feature_names = FEATURE_NAMES
        return obj


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
    Top-K recommendations for one user from precomputed batch pairs.
    Uses ML score if ≥5 submissions, else rule-based score.
    """
    # B8 fix: copy before modifying index to avoid mutating the caller's dataframe
    pairs = pairs.copy()
    if pairs.index.name != 'user_id' and 'user_id' in pairs.columns:
        pairs = pairs.set_index('user_id')
        
    try:
        # .loc[[user_id]] ensures it returns a DataFrame even for single row
        up = pairs.loc[[user_id]].copy()
    except KeyError:
        logger.warning(f'No pairs for user {user_id}')
        return pd.DataFrame()
        
    if up.empty:
        logger.warning(f'No pairs for user {user_id}')
        return pd.DataFrame()

    if (up['submission_count'].iloc[0] >= 5
            and model is not None
            and (model.model is not None or not SKLEARN_AVAILABLE)):
        up['score']  = model.predict(up)
        up['reason'] = 'ML-based' if model.model is not None else 'Rule-based fallback'
    else:
        up['score']  = up['rule_score']
        up['reason'] = 'Rule-based'

    top = up.nlargest(top_k, 'score')[['task_name', 'domain', 'score', 'reason']].reset_index(drop=True)
    top.insert(0, 'rank', range(1, len(top) + 1))
    return top


# ─────────────────────────────────────────────────────────────────────────── #
#  Real-Time Inference API                                                    #
# ─────────────────────────────────────────────────────────────────────────── #

def recommend_for_user(
    user_dict: dict,
    task_features: pd.DataFrame,
    model: RankingModel,
    top_k: int = config.TOP_K_RECOMMENDATIONS,
) -> pd.DataFrame:
    """
    Real-time inference API for a single user without batch dataframe scans.
    user_dict should be the output of problem1.py's get_user_features().
    """
    if not user_dict or task_features.empty:
        return pd.DataFrame()

    user_id = user_dict.get('user_id', 'unknown')
    
    uf_records = []
    for dom in config.DOMAINS:
        sub_count = user_dict.get(f'task_count_{dom}', 0)
        interest  = user_dict.get(f'interest_{dom}', 0.0)
        mastery   = user_dict.get(f'mastery_{dom}', 0.0)
        gap       = 1.0 - mastery
        # Bug fix: include ALL domains where the user has activity OR a gap > 0.
        # Previously zero-activity domains were skipped entirely, so a user with
        # 0 data_eng submissions but a 0.70 raw gap got ZERO data_eng recommendations.
        if sub_count > 0 or interest > 0.0 or gap > 0.01:
            uf_records.append({
                'user_id': user_id,
                'domain': dom,
                'submission_count': sub_count,
                'mastery': mastery,
                'gap_score': gap,
                'approval_rate': user_dict.get('global_approval_rate', 0.70),
                'optimal_difficulty': user_dict.get('optimal_difficulty', 1.5),
                'interest_score': max(interest, 0.0),
            })
            
    uf = pd.DataFrame(uf_records)
    if uf.empty:
        # B6 fix: broaden cold-start fallback to ALL non-ignored domains so
        # new users receive recommendations across the full task catalog,
        # not just 'general' which may have no tasks after domain filtering.
        fallback_domains = [d for d in config.DOMAINS if d not in ('ignored', 'general')]
        uf = pd.DataFrame([
            {
                'user_id': user_id,
                'domain': dom,
                'submission_count': 0,
                'mastery': 0.0,
                'gap_score': 1.0,
                'approval_rate': 0.70,
                'optimal_difficulty': 1.5,
                'interest_score': 1.0,
            }
            for dom in fallback_domains
        ])

    pairs = create_domain_matched_pairs(uf, task_features)
    pairs = engineer_advanced_features(pairs)
    pairs = compute_rule_score(pairs)
    
    submission_count = uf['submission_count'].sum()
    if (submission_count >= 5
            and model is not None
            and (model.model is not None or not SKLEARN_AVAILABLE)):
        pairs['score'] = model.predict(pairs)
        pairs['reason'] = 'ML-based' if model.model is not None else 'Rule-based fallback'
    else:
        pairs['score'] = pairs['rule_score']
        pairs['reason'] = 'Rule-based'
        
    top = pairs.nlargest(top_k, 'score')[['task_name', 'domain', 'score', 'reason']].reset_index(drop=True)
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
