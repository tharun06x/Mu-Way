import logging
import pandas as pd
from django.core.management.base import BaseCommand
from roadmap.models import TaskCatalog, UserSubmission
from data_loader import DataLoader
import numpy as np

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Import data from Excel files into the database'

    def handle(self, *args, **options):
        self.stdout.write("Loading data using existing DataLoader logic...")
        
        # DataLoader handles reading from config.QUERY_FILE and config.KARMA_FILE
        # and applies the necessary renaming and synthethic approvals.
        loader = DataLoader()
        try:
            user_data, task_data, _ = loader.load_all()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to load data: {e}"))
            return

        self.stdout.write(f"Loaded {len(user_data)} submissions and {len(task_data)} tasks. Importing to DB...")

        # 1. Import TaskCatalog
        self.stdout.write("Clearing existing TaskCatalog...")
        TaskCatalog.objects.all().delete()
        
        task_objs = []
        for _, row in task_data.iterrows():
            # difficulty_level is returned by load_task_data or enriched. 
            task_objs.append(TaskCatalog(
                task_name=row['task_name'],
                domain=row.get('domain', ''),
                task_karma_value=row.get('task_karma_value', 0) if pd.notnull(row.get('task_karma_value')) else 0,
                difficulty_level=row.get('difficulty_level', 2) if pd.notnull(row.get('difficulty_level')) else 2,
                task_type=row.get('task_type', '') if pd.notnull(row.get('task_type')) else ''
            ))
            
        self.stdout.write("Bulk creating tasks...")
        TaskCatalog.objects.bulk_create(task_objs, batch_size=1000)

        # 2. Import UserSubmissions
        self.stdout.write("Clearing existing UserSubmissions...")
        UserSubmission.objects.all().delete()
        
        # query.xlsx is very large (13MB), bulk insert in chunks
        user_objs = []
        for idx, row in user_data.iterrows():
            # Safely handle NaN values, replace with None or default
            sub_date = row['submission_date']
            if pd.isnull(sub_date):
                sub_date = None

            user_objs.append(UserSubmission(
                user_id=row['user_id'],
                domain=row.get('domain', ''),
                task_name=row['task_name'],
                task_id=row.get('task_id', 0),
                submission_date=sub_date,
                is_approved=row.get('is_approved', False),
                difficulty_level=row.get('difficulty_level', 2)
            ))
            
            # Commit in batches of 5000 to save memory
            if len(user_objs) >= 5000:
                UserSubmission.objects.bulk_create(user_objs)
                user_objs = []
                self.stdout.write(f"Inserted {idx} records...")
                
        # Insert remaining
        if user_objs:
            UserSubmission.objects.bulk_create(user_objs)

        self.stdout.write(self.style.SUCCESS("Successfully imported all data to the database!"))
