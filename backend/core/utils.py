"""
core/utils.py — Shared utility functions used across multiple core modules.
"""

import pandas as pd


def normalize_task_name(value) -> str:
    """
    Normalize task names to a canonical lowercase key.

    Used for reliable deduplication and done-task filtering.
    Examples:
        'React Basics '  → 'react basics'
        'Two  Sum'       → 'two sum'
        None / NaN       → ''
    """
    if pd.isna(value):
        return ''
    return ' '.join(str(value).strip().lower().split())
