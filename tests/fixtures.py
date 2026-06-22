"""Shared test fixtures."""

import pandas as pd


def sample_submissions():
    """Minimal user submission history using real hashtag format domains."""
    return pd.DataFrame({
        "user_id": ["u1", "u1", "u2", "u2", "u2"],
        "domain": ["#cl-ai-basicintro", "#cl-ds-linreg", "#cl-web-frontend",
                   "#cl-web-react", "#cl-dsa-twosum"],
        "task_name": ["AI Intro", "Linear Regression", "React Basics",
                      "Web Frontend", "Two Sum"],
        "task_id": [1, 2, 3, 4, 5],
        "submission_date": pd.to_datetime(
            ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04", "2026-01-05"]
        ),
        "is_approved": [1, 0, 1, 1, 0],
        "difficulty_level": [1.0, 2.0, 1.0, 2.0, 2.0],
    })


def sample_tasks():
    """Minimal task catalog mirroring the submission domains."""
    return pd.DataFrame({
        "task_name": ["AI Intro", "Linear Regression", "React Basics",
                      "Web Frontend", "Two Sum"],
        "domain": ["#cl-ai-basicintro", "#cl-ds-linreg", "#cl-web-frontend",
                   "#cl-web-react", "#cl-dsa-twosum"],
        "difficulty_level": [1.0, 2.0, 1.0, 2.0, 2.0],
        "task_karma_value": [100, 200, 100, 150, 200],
        "complexity": ["Low", "Medium", "Low", "Medium", "Medium"],
        "task_type": ["Learning", "Learning", "Learning", "Learning", "Challenge"],
    })
