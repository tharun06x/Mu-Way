"""Tests for the ranking model and prediction pipeline."""

from career_roadmap.models import predict, train_ranker
from tests.fixtures import sample_submissions, sample_tasks


def test_train_ranker_returns_pairs():
    """train_ranker should return (model, pairs_df, metrics_dict)."""
    model, pairs, metrics = train_ranker(sample_submissions(), sample_tasks(), save_model=False)
    assert pairs is not None and len(pairs) > 0, "pairs DataFrame must be non-empty"
    assert "rule_score" in pairs.columns, "pairs must have a rule_score column"
    assert isinstance(metrics, dict), "metrics must be a dict"
    # ndcg may be 0.0 for tiny datasets but must be present
    assert "ndcg" in metrics or "model_type" in metrics


def test_predict_returns_ranked_tasks():
    """predict() should return a DataFrame with sequential rank column."""
    model, pairs, _ = train_ranker(sample_submissions(), sample_tasks(), save_model=False)
    user_id = pairs["user_id"].iloc[0]
    recs = predict(user_id, pairs, model=model, top_k=2)
    assert len(recs) > 0, "predict must return at least one recommendation"
    assert "rank" in recs.columns, "result must have a rank column"
    assert list(recs["rank"]) == list(range(1, len(recs) + 1)), "ranks must be sequential from 1"
