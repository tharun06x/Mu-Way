"""Data loading, cleaning, and feature-engineering entry points."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import re
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

##(new function added in 2024-06-05)
def clean_data(df: pd.DataFrame, is_task_data: bool = False) -> pd.DataFrame:
    """Apply shared cleaning rules used by downstream modules."""
    cleaned = df.copy()
    
    # 1. Standardize column names
    cleaned.columns = cleaned.columns.str.strip().str.lower()
    
    # 2. Clean submission dates (for user tracking)
    if "submission_date" in cleaned.columns:
        cleaned["submission_date"] = pd.to_datetime(cleaned["submission_date"], errors="coerce")
        cleaned = cleaned.dropna(subset=["submission_date"])
        
    # 3. Filter out team members
    if "is_team_member" in cleaned.columns:
        cleaned = cleaned[~cleaned["is_team_member"].fillna(False).astype(bool)]

    #NEW: Domain Cleaning & Mapping
    # Rename the messy Excel column to our standard 'domain'
    if "interest group" in cleaned.columns:
        cleaned = cleaned.rename(columns={"interest group": "domain"})

    if "domain" in cleaned.columns:
        cleaned["domain"] = cleaned["domain"].astype(str).str.strip().str.lower()
        
        # Map raw Excel names to our config.py canonical aliases
        domain_mapping = {
            "artificial intelligence": "ai",
            "generative ai": "ai",
            "ai": "ai",
            "data science": "ds",
            "data analytics": "ds",
            "data structures and algorithm": "dsa",
            "data structures and algorithms": "dsa",
            "web development": "web",
            "cybersecurity": "cybersec",
            "cyber security": "cybersec",
            "devops": "devops",
            "game-dev": "general",       # Mapping niche topics to general foundation
            "no/low code": "general",
            "quantum computing": "general"
        }
        
        # Apply mapping; if an unknown domain appears, default it safely to 'general'
        cleaned["domain"] = cleaned["domain"].map(lambda x: domain_mapping.get(x, "general"))

    # --- NEW: Time Parsing Helper Function ---
    def parse_time_to_minutes(time_val) -> int:
        if pd.isna(time_val):
            return 60  # Default to 60 mins if completely blank
            
        time_str = str(time_val).lower().strip()
        
        # Extract all numbers (e.g., "1-2" becomes [1.0, 2.0])
        numbers = [float(n) for n in re.findall(r'\d+\.?\d*', time_str)]
        
        if not numbers:
            return 60  # Default if no numbers found
            
        # If it's a range like "1-2 hours", take the upper bound (2.0)
        val = max(numbers)
        
        # Convert to minutes based on the text found
        if 'day' in time_str:
            # Assuming 1 "day" of study = 4 hours (240 mins) of actual work
            minutes = int(val * 240)
        elif 'hr' in time_str or 'hour' in time_str:
            minutes = int(val * 60)
        elif 'min' in time_str:
            minutes = int(val)
        else:
            # Fallback assumption if they just typed "2" 
            minutes = int(val * 60) 
            
        # SAFETY CAP: Prevent a massive task from breaking the weekly budget loop
        import config
        max_allowed = getattr(config, 'MINUTES_PER_WEEK', 180)
        return min(minutes, max_allowed)

    # --- NEW: Apply Time Parsing ---
    # We only run this if we are cleaning the Task Catalog, not the User History
    if is_task_data:
        time_col = 'time required' if 'time required' in cleaned.columns else 'estimated_minutes'
        
        if time_col in cleaned.columns:
            cleaned["estimated_minutes"] = cleaned[time_col].apply(parse_time_to_minutes)
        else:
            cleaned["estimated_minutes"] = 60

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
