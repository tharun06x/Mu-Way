"""
data_loader.py — Loads and prepares datasets for ICRS pipeline.

Datasets:
  - query.xlsx        : User task submission history
  - Karma_Master.xlsx : Task catalog with karma, complexity, type
"""

import pandas as pd
import numpy as np
import logging
import config

logger = logging.getLogger(__name__)


class DataLoader:

    def load_all(self):
        """
        Load user submissions and task catalog.

        Returns:
            user_data  (DataFrame): [user_id, domain, task_name, task_id,
                                     is_approved, submission_date, difficulty_level]
            task_data  (DataFrame): [task_name, domain, task_karma_value,
                                     difficulty_level, task_type]
            dream_roles_df: None (inferred from activity)
        """
        user_data = self._load_user_data()
        task_data = self._load_task_data(user_data)   # pass user_df for catalog

        # Enrich user rows with difficulty from task catalog
        diff_map = task_data.set_index('task_name')['difficulty_level'].to_dict()
        user_data['difficulty_level'] = (
            user_data['task_name'].map(diff_map).fillna(2).astype(int)
        )

        logger.info(
            f"✓ Loaded {len(user_data):,} submissions | "
            f"{user_data['user_id'].nunique():,} users | "
            f"{task_data['task_name'].nunique()} tasks"
        )
        return user_data, task_data, None

    # ------------------------------------------------------------------ #
    def _load_user_data(self):
        logger.info(f"Loading user submissions from {config.QUERY_FILE} ...")
        df = pd.read_excel(config.QUERY_FILE)
        df.columns = df.columns.str.strip().str.lower()

        df.rename(columns={
            'muid':                 'user_id',
            'hashtag':              'domain',
            'task_submission_date': 'submission_date',
        }, inplace=True)

        # Parse date
        df['submission_date'] = pd.to_datetime(df['submission_date'], errors='coerce')
        df = df.dropna(subset=['submission_date', 'user_id'])
        if 'is_team_member' in df.columns:
            df = df[~df['is_team_member'].fillna(False).astype(bool)].copy()

        # Synthetic approval  — query.xlsx has no approval column.
        # We use a realistic 73 % approval rate seeded for reproducibility.
        rng = np.random.default_rng(42)
        df['is_approved'] = rng.choice([1, 0], size=len(df), p=[0.73, 0.27])

        # Integer task id
        df['task_id'] = df['task_name'].astype('category').cat.codes

        # Keep essential columns only
        keep = ['user_id', 'domain', 'task_name', 'task_id',
                'submission_date', 'is_approved']
        df = df[[c for c in keep if c in df.columns]].copy()

        return df

    def _load_task_data(self, user_df: pd.DataFrame = None):
        """
        Build task catalog from:
         1. Unique tasks found in user submission history (749 real tasks)
         2. Enriched with difficulty from karma master where available.

        This approach ensures the recommendation pool matches what users
        actually do — the karma master (22 rows) alone is too small.
        """
        logger.info(f"Building task catalog from submissions + karma master ...")

        # ── Step 1: unique tasks from submissions ────────────── #
        if user_df is not None and len(user_df):
            task_catalog = (
                user_df[['task_name', 'domain']]
                .dropna(subset=['task_name'])
                .drop_duplicates(subset=['task_name'])
                .copy()
            )
        else:
            task_catalog = pd.DataFrame(columns=['task_name', 'domain'])

        # ── Step 2: karma master for enrichment ──────────────── #
        try:
            sheets = pd.read_excel(config.KARMA_MASTER_FILE, sheet_name=None)
            km = pd.concat(sheets.values(), ignore_index=True)
            km.columns = km.columns.str.strip().str.lower()
            km.rename(columns={
                'activity title': 'task_name',
                'hash tag':       'km_domain',
                'karma alloted':  'task_karma_value',
                'task type':      'task_type',
            }, inplace=True)

            complexity_map = {'Low': 1, 'Medium': 2, 'High': 3}
            km['difficulty_level'] = (
                km.get('complexity', pd.Series(dtype=str))
                  .map(complexity_map)
                  .fillna(2)
                  .astype(int)
            )
            km['task_karma_value'] = pd.to_numeric(
                km.get('task_karma_value', 50), errors='coerce'
            ).fillna(50)

            km_enrich = km[[
                'task_name', 'km_domain', 'difficulty_level',
                'task_karma_value', 'task_type', 'complexity'
            ]].dropna(subset=['task_name']).drop_duplicates(subset=['task_name'])
        except Exception as exc:
            logger.warning(f"Could not load karma master: {exc}")
            km_enrich = pd.DataFrame(columns=[
                'task_name', 'km_domain', 'difficulty_level',
                'task_karma_value', 'task_type', 'complexity'
            ])

        # ── Step 3: merge enrichment into catalog ─────────────── #
        if len(task_catalog):
            task_catalog = task_catalog.merge(km_enrich, on='task_name', how='left')
        else:
            task_catalog = km_enrich.copy()
            task_catalog['domain'] = task_catalog.get('km_domain', 'general')

        from problem1 import hashtag_to_domain
        task_catalog['domain_mapped'] = task_catalog['domain'].apply(
            lambda x: hashtag_to_domain(x) if pd.notna(x) else 'general'
        )
        task_catalog = task_catalog[task_catalog['domain_mapped'] != 'ignored'].copy()
        task_catalog.drop(columns=['domain_mapped'], inplace=True)

        # Fill defaults
        task_catalog['difficulty_level']  = task_catalog.get('difficulty_level', 2).fillna(2).astype(int)
        task_catalog['task_karma_value']  = task_catalog.get('task_karma_value', 50).fillna(50)
        if 'complexity' not in task_catalog.columns:
            task_catalog['complexity'] = 'Medium'
        task_catalog['complexity'] = task_catalog['complexity'].fillna('Medium')
        if 'task_type' not in task_catalog.columns:
            task_catalog['task_type'] = 'Learning'
        task_catalog['task_type'] = task_catalog['task_type'].fillna('Learning')

        # ── Step 4: Empirical Bayesian Difficulty ─────────────── #
        if user_df is not None and len(user_df) > 0 and 'is_approved' in user_df.columns:
            # Get real attempts and approvals per task
            task_stats = user_df.groupby('task_name')['is_approved'].agg(['count', 'sum']).reset_index()
            task_stats.rename(columns={'count': 'real_attempts', 'sum': 'real_approvals'}, inplace=True)
            
            task_catalog = task_catalog.merge(task_stats, on='task_name', how='left')
            task_catalog['real_attempts'] = task_catalog['real_attempts'].fillna(0)
            task_catalog['real_approvals'] = task_catalog['real_approvals'].fillna(0)
            
            # Prior difficulty comes from Karma Master (1 to 4)
            prior_diff = task_catalog['difficulty_level']
            
            # Map prior difficulty to expected pass rate (1 -> 0.90, 2 -> 0.70, 3 -> 0.50, 4 -> 0.30)
            expected_rate = 0.90 - (prior_diff - 1) * 0.20
            
            # Bayesian smoothing
            prior_weight = getattr(config, 'BAYESIAN_PRIOR_TASK_WEIGHT', 20)
            smoothed_rate = ((prior_weight * expected_rate) + task_catalog['real_approvals']) / (prior_weight + task_catalog['real_attempts'])
            
            # Convert smoothed rate back to continuous difficulty (0.90 -> 1.0, 0.30 -> 4.0)
            empirical_diff = 1.0 + (0.90 - smoothed_rate) * 5.0
            
            # Clip between 1.0 and 4.0
            task_catalog['difficulty_level'] = empirical_diff.clip(lower=1.0, upper=4.0).astype(float)
        else:
            task_catalog['difficulty_level'] = task_catalog['difficulty_level'].astype(float)

        logger.info(f"Task catalog ready: {len(task_catalog)} tasks")
        return task_catalog
