"""Shared test fixtures."""

import pandas as pd


def sample_submissions():
    return pd.DataFrame({
        "user_id": ["u1", "u1", "u2"],
        "domain": ["#cl-ai-intro", "#cl-ds-linreg", "#cl-web-react"],
        "task_name": ["AI Intro", "Linear Regression", "React Basics"],
        "task_id": [1, 2, 3],
        "submission_date": pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-03"]),
        "is_approved": [1, 0, 1],
        "difficulty_level": [1, 2, 1],
    })


def sample_tasks():
    return pd.DataFrame({
        "task_name": ["AI Intro", "Linear Regression", "React Basics"],
        "domain": ["#cl-ai-intro", "#cl-ds-linreg", "#cl-web-react"],
        "difficulty_level": [1, 2, 1],
        "task_karma_value": [100, 200, 100],
        "complexity": ["Low", "Medium", "Low"],
    })
