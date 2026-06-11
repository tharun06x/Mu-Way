"""Data loading, cleaning, and feature-engineering entry points."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .utils import ensure_project_root_on_path


def load_data(data_dir: str | Path | None = None):
    """Load submissions and task catalog using the production loader."""
    ensure_project_root_on_path()
    import config
    from data_loader import DataLoader

    old_data_dir = config.DATA_DIR
    if data_dir is not None:
        config.DATA_DIR = Path(data_dir)
        config.QUERY_FILE = config.DATA_DIR / "query.xlsx"
        config.KARMA_MASTER_FILE = config.DATA_DIR / "Karma Master - Software(1).xlsx"
    try:
        return DataLoader().load_all()
    finally:
        config.DATA_DIR = old_data_dir
        config.QUERY_FILE = config.DATA_DIR / "query.xlsx"
        config.KARMA_MASTER_FILE = config.DATA_DIR / "Karma Master - Software(1).xlsx"


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Apply shared cleaning rules used by downstream modules."""
    cleaned = df.copy()
    cleaned.columns = cleaned.columns.str.strip().str.lower()
    if "submission_date" in cleaned.columns:
        cleaned["submission_date"] = pd.to_datetime(cleaned["submission_date"], errors="coerce")
        cleaned = cleaned.dropna(subset=["submission_date"])
    if "is_team_member" in cleaned.columns:
        cleaned = cleaned[~cleaned["is_team_member"].fillna(False).astype(bool)]
    return cleaned


def compute_features(
    user_data: pd.DataFrame,
    task_data: pd.DataFrame | None = None,
    output_path: str | Path | None = None,
) -> pd.DataFrame:
    """Build the Problem 1 feature store."""
    ensure_project_root_on_path()
    from problem1 import build_feature_store

    features = build_feature_store(user_data, task_data, save=False)
    if output_path is not None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if output_path.suffix == ".parquet":
            features.to_parquet(output_path, index=False)
        else:
            features.to_pickle(output_path)
    return features
