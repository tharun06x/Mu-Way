from career_roadmap.data import compute_features
from career_roadmap.models import train_ranker
from tests.fixtures import sample_submissions, sample_tasks


def test_data_to_models_handoff():
    features = compute_features(sample_submissions(), sample_tasks())
    _, pairs, _ = train_ranker(sample_submissions(), sample_tasks(), save_model=False)
    assert len(features) > 0
    assert len(pairs) > 0
