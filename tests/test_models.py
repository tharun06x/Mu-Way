from career_roadmap.models import predict, train_ranker
from tests.fixtures import sample_submissions, sample_tasks


def test_train_ranker_returns_pairs():
    model, pairs, metrics = train_ranker(sample_submissions(), sample_tasks(), save_model=False)
    assert len(pairs) > 0
    assert "rule_score" in pairs.columns
    assert "ndcg" in metrics


def test_predict_returns_ranked_tasks():
    model, pairs, _ = train_ranker(sample_submissions(), sample_tasks(), save_model=False)
    recs = predict("u1", pairs, model=model, top_k=2)
    assert list(recs["rank"]) == [1, 2]
