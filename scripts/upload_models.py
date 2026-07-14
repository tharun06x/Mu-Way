#!/usr/bin/env python
"""
scripts/upload_models.py
────────────────────────
One-time script: push your existing local model artifacts to Supabase Storage.

Run this once from the project root AFTER setting SUPABASE_URL and
SUPABASE_SERVICE_KEY in your .env (or exporting them to the environment).

    python scripts/upload_models.py

After this, the app will auto-download these files on every fresh deploy.
"""

import sys
import os
from pathlib import Path

# Bootstrap path so we can import from backend/core
ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

# Load .env from project root
from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

# Set up Django (needed to import core.config.settings)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "icrs.settings")

import django
django.setup()

from core.config import settings as cfg
from core import storage

print("=" * 60)
print("  ICRS — Upload Model Artifacts to Supabase Storage")
print("=" * 60)
print(f"\n  Bucket   : {storage.BUCKET_NAME}")
print(f"  Endpoint : {storage.SUPABASE_URL}")
print()

storage.push_all_models(cfg.OUTPUT_DIR)

print()
print("✅ Done! Your models are now stored in Supabase Storage.")
print("   On the next fresh deploy, the app will auto-download them.")
