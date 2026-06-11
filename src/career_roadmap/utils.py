"""Utility helpers shared by the package wrappers."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def project_root() -> Path:
    """Return the repository root for this package checkout."""
    return Path(__file__).resolve().parents[2]


def ensure_project_root_on_path() -> Path:
    """Allow package modules to call the existing legacy runner modules."""
    root = project_root()
    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    return root


def normalize_task_name(value: Any) -> str:
    """Normalize task names for matching completed tasks to catalog rows."""
    if value is None:
        return ""
    return " ".join(str(value).strip().lower().split())


def load_json(path: str | Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)
