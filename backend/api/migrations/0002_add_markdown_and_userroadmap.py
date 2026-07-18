# Migration 0002: Add markdown_detail and create UserRoadmap table.
# Uses RunSQL to target the actual table names (roadmap_taskcatalog / roadmap_userroadmap)
# because the 0001 migration was applied against pre-existing tables, creating a mismatch
# between Django's expected table name (api_taskcatalog) and the real one (roadmap_taskcatalog).

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0001_initial'),
    ]

    operations = [
        # ── 1. Add markdown_detail column to the existing task catalog ─────── #
        migrations.RunSQL(
            sql="ALTER TABLE roadmap_taskcatalog ADD COLUMN markdown_detail TEXT NULL;",
            reverse_sql="SELECT 1;",  # SQLite cannot drop columns; no-op on rollback
        ),

        # ── 2. Create the UserRoadmap persistence table ────────────────────── #
        migrations.RunSQL(
            sql="""
            CREATE TABLE IF NOT EXISTS roadmap_userroadmap (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     VARCHAR(255) NOT NULL,
                role        VARCHAR(255) NOT NULL,
                roadmap_data TEXT NOT NULL,
                created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (user_id, role)
            );
            CREATE INDEX IF NOT EXISTS roadmap_userroadmap_user_id
                ON roadmap_userroadmap (user_id);
            """,
            reverse_sql="DROP TABLE IF EXISTS roadmap_userroadmap;",
        ),
    ]
