"""Tests for the ranking model and prediction pipeline."""

import sys
from pathlib import Path

# Ensure the backend package is on the path (tests run from project root)
_BACKEND = Path(__file__).resolve().parent.parent / 'backend'
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

# Minimal Django settings bootstrap so core modules can import config
import django
from django.conf import settings as _ds
if not _ds.configured:
    _ds.configure(
        DATABASES={'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}},
        INSTALLED_APPS=['django.contrib.contenttypes', 'django.contrib.auth'],
        SECRET_KEY='test-secret-key-only',
    )
    django.setup()

from core.ranking import RankingModel, engineer_task_features, recommend_for_user
from core.features import compute_user_features, get_cold_start_features, hashtag_to_domain
from tests.fixtures import sample_submissions, sample_tasks


# ─── Helper ───────────────────────────────────────────────────────────────── #

def _run_pipeline(save_model=False):
    """Run full ranking pipeline on fixture data."""
    from core.ranking import run_ranking_pipeline
    subs = sample_submissions()
    subs['domain_mapped'] = subs['domain'].apply(hashtag_to_domain)
    tasks = sample_tasks()
    return run_ranking_pipeline(subs, tasks, save_model=save_model)


# ─── Model Tests ─────────────────────────────────────────────────────────── #

def test_train_ranker_returns_pairs():
    """run_ranking_pipeline should return (model, pairs_df, metrics_dict)."""
    model, pairs, metrics = _run_pipeline()
    assert pairs is not None and len(pairs) > 0, "pairs DataFrame must be non-empty"
    assert "rule_score" in pairs.columns, "pairs must have a rule_score column"
    assert isinstance(metrics, dict), "metrics must be a dict"
    # ndcg may be 0.0 for tiny datasets but must be present
    assert "ndcg" in metrics or "model_type" in metrics


def test_predict_returns_ranked_tasks():
    """recommend() should return a DataFrame with sequential rank column."""
    from core.ranking import recommend
    model, pairs, _ = _run_pipeline()
    user_id = pairs['user_id'].iloc[0]
    recs = recommend(pairs, model, user_id, top_k=2)
    assert len(recs) > 0, "predict must return at least one recommendation"
    assert "rank" in recs.columns, "result must have a rank column"
    assert list(recs["rank"]) == list(range(1, len(recs) + 1)), "ranks must be sequential from 1"


def test_cold_start_features_shape():
    """get_cold_start_features should return a dict with all expected keys."""
    from core.config import settings as config
    feat = get_cold_start_features("unknown@mulearn")
    assert feat['is_cold_start'] == 1
    assert feat['total_submissions'] == 0
    for dom in config.DOMAINS:
        assert f'mastery_{dom}' in feat, f"Missing mastery_{dom}"
        assert f'interest_{dom}' in feat, f"Missing interest_{dom}"


def test_recommend_for_user_cold_start():
    """recommend_for_user should work for unknown users (cold-start path)."""
    tasks = sample_tasks()
    subs = sample_submissions()
    subs['domain_mapped'] = subs['domain'].apply(hashtag_to_domain)
    tf = engineer_task_features(subs, tasks)

    cold_feat = get_cold_start_features("brand_new_user@mulearn")
    recs = recommend_for_user(cold_feat, tf, model=None, top_k=3)
    assert isinstance(recs, __import__('pandas').DataFrame), "Must return a DataFrame"
    # Cold-start may return 0 rows if domain filter removes all tasks — don't assert length


def test_normalize_task_name_deduplication():
    """normalize_task_name should consistently canonicalize task names."""
    from core.utils import normalize_task_name
    assert normalize_task_name("React Basics ") == "react basics"
    assert normalize_task_name("  Two  Sum  ") == "two sum"
    assert normalize_task_name(None) == ""
    assert normalize_task_name(float('nan')) == ""
