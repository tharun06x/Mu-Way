from career_roadmap.data import clean_data, compute_features
from tests.fixtures import sample_submissions, sample_tasks


def test_clean_data_keeps_valid_submission_rows():
    cleaned = clean_data(sample_submissions())
    assert len(cleaned) == 3
    assert "submission_date" in cleaned.columns


def test_compute_features_returns_user_rows():
    features = compute_features(sample_submissions(), sample_tasks())
    assert set(features["user_id"]) == {"u1", "u2"}
    assert "mastery_ai" in features.columns
