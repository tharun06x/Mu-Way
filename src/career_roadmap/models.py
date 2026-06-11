"""Model training and recommendation wrappers."""

from __future__ import annotations

import pandas as pd

from .utils import ensure_project_root_on_path


def train_ranker(user_data: pd.DataFrame, task_data: pd.DataFrame, save_model: bool = True):
    """Train the ranking pipeline, or use the rule-based fallback if needed."""
    ensure_project_root_on_path()
    from problem3_runner import run_ranking_pipeline

    return run_ranking_pipeline(user_data, task_data, save_model=save_model)


def predict(
    user_id: str,
    pairs: pd.DataFrame,
    model=None,
    top_k: int = 5,
) -> pd.DataFrame:
    """Return top ranked tasks for one user from a prepared pair table."""
    ensure_project_root_on_path()
    from problem3_runner import recommend

    return recommend(pairs, model, user_id, top_k=top_k)
