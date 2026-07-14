"""
data_loader.py — Loads datasets for ICRS pipeline from the Database.
"""

import pandas as pd
import logging
from api.models import TaskCatalog, UserSubmission
from core.config import settings as config

logger = logging.getLogger(__name__)


class DataLoader:

    def load_all(self):
        """
        Load user submissions and task catalog from the Database.

        Returns:
            user_data  (DataFrame): [user_id, domain, task_name, task_id,
                                     is_approved, submission_date, difficulty_level]
            task_data  (DataFrame): [task_name, domain, task_karma_value,
                                     difficulty_level, task_type]
            dream_roles_df: None (inferred from activity)
        """
        logger.info("Loading data from Supabase/PostgreSQL via Django ORM...")

        # Load user submissions
        user_qs = UserSubmission.objects.all().values(
            'user_id', 'domain', 'task_name', 'task_id', 
            'submission_date', 'is_approved', 'difficulty_level'
        )
        user_data = pd.DataFrame.from_records(user_qs)
        
        if user_data.empty:
            user_data = pd.DataFrame(columns=[
                'user_id', 'domain', 'task_name', 'task_id', 
                'submission_date', 'is_approved', 'difficulty_level'
            ])

        # Load task catalog
        task_qs = TaskCatalog.objects.all().values(
            'task_name', 'domain', 'task_karma_value', 'difficulty_level', 'task_type'
        )
        task_data = pd.DataFrame.from_records(task_qs)
        
        if task_data.empty:
            task_data = pd.DataFrame(columns=[
                'task_name', 'domain', 'task_karma_value', 'difficulty_level', 'task_type'
            ])

        # ── Step 4: Empirical Bayesian Difficulty ─────────────── #
        if not user_data.empty and 'is_approved' in user_data.columns:
            task_stats = user_data.groupby('task_name')['is_approved'].agg(['count', 'sum']).reset_index()
            task_stats.rename(columns={'count': 'real_attempts', 'sum': 'real_approvals'}, inplace=True)
            
            task_data = task_data.merge(task_stats, on='task_name', how='left')
            task_data['real_attempts'] = task_data['real_attempts'].fillna(0)
            task_data['real_approvals'] = task_data['real_approvals'].fillna(0)
            
            prior_diff = task_data['difficulty_level']
            expected_rate = 0.90 - (prior_diff - 1) * 0.20
            
            prior_weight = getattr(config, 'BAYESIAN_PRIOR_TASK_WEIGHT', 20)
            smoothed_rate = ((prior_weight * expected_rate) + task_data['real_approvals']) / (prior_weight + task_data['real_attempts'])
            
            empirical_diff = 1.0 + (0.90 - smoothed_rate) * 5.0
            task_data['difficulty_level'] = empirical_diff.clip(lower=1.0, upper=4.0).astype(float)
        else:
            task_data['difficulty_level'] = task_data['difficulty_level'].astype(float)


        logger.info(
            f"✓ Loaded {len(user_data):,} submissions | "
            f"{user_data['user_id'].nunique() if not user_data.empty else 0:,} users | "
            f"{len(task_data)} tasks"
        )
        
        return user_data, task_data, None
