from career_roadmap.data import clean_data, compute_features
from tests.fixtures import sample_submissions, sample_tasks


def test_clean_data_keeps_valid_submission_rows():
    cleaned = clean_data(sample_submissions())
    # All 5 rows have valid submission_date — none should be dropped
    assert len(cleaned) == 5
    assert "submission_date" in cleaned.columns


def test_compute_features_returns_user_rows():
    features = compute_features(sample_submissions(), sample_tasks())
    # feature store is indexed by user_id; reset to get the column
    features_reset = features.reset_index()
    assert set(features_reset["user_id"]) == {"u1", "u2"}
    # At least one domain mastery column should be present
    mastery_cols = [c for c in features.columns if c.startswith("mastery_")]
    assert len(mastery_cols) > 0
