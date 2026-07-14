"""
core/storage.py — Supabase Storage utility for ICRS model files.

Handles downloading model artifacts (feature_store.pkl, ranking_model.pkl, etc.)
from Supabase Storage on startup, and uploading them after retraining.

Required env vars:
    SUPABASE_URL        — your project URL (e.g. https://xxxx.supabase.co)
    SUPABASE_SERVICE_KEY — service role key (not the anon key)
    SUPABASE_BUCKET     — storage bucket name (default: "icrs-models")
"""

import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
BUCKET_NAME = os.getenv("SUPABASE_BUCKET", "icrs-models")


def _get_client():
    """Return a Supabase client. Raises if credentials are missing."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise EnvironmentError(
            "SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in your .env file "
            "to use Supabase Storage."
        )
    from supabase import create_client
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def download_file(remote_path: str, local_path: Path, overwrite: bool = False) -> bool:
    """
    Download a single file from Supabase Storage to local disk.

    Args:
        remote_path: Path inside the bucket  (e.g. "models/ranking_model.pkl")
        local_path:  Destination on disk     (e.g. Path("output/ranking_model.pkl"))
        overwrite:   Re-download even if file already exists locally.

    Returns:
        True if downloaded, False if skipped (already exists).
    """
    if local_path.exists() and not overwrite:
        logger.info(f"  ✓ {local_path.name} already exists locally — skipping download.")
        return False

    logger.info(f"  ↓ Downloading {remote_path} from Supabase Storage …")
    try:
        client = _get_client()
        data: bytes = client.storage.from_(BUCKET_NAME).download(remote_path)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(data)
        logger.info(f"  ✓ Saved → {local_path} ({len(data) / 1_048_576:.1f} MB)")
        return True
    except Exception as exc:
        logger.warning(f"  ✗ Could not download {remote_path}: {exc}")
        return False


def upload_file(local_path: Path, remote_path: str) -> bool:
    """
    Upload a local file to Supabase Storage (upsert — overwrites existing).

    Args:
        local_path:  Source file on disk    (e.g. Path("output/ranking_model.pkl"))
        remote_path: Destination in bucket  (e.g. "models/ranking_model.pkl")

    Returns:
        True on success, False on failure.
    """
    if not local_path.exists():
        logger.warning(f"  ✗ Upload skipped — {local_path} does not exist.")
        return False

    logger.info(f"  ↑ Uploading {local_path.name} to Supabase Storage …")
    try:
        client = _get_client()
        with open(local_path, "rb") as f:
            client.storage.from_(BUCKET_NAME).upload(
                path=remote_path,
                file=f,
                file_options={"upsert": "true", "content-type": "application/octet-stream"},
            )
        size_mb = local_path.stat().st_size / 1_048_576
        logger.info(f"  ✓ Uploaded → {remote_path} ({size_mb:.1f} MB)")
        return True
    except Exception as exc:
        logger.warning(f"  ✗ Could not upload {local_path.name}: {exc}")
        return False


# ── Convenience wrappers for the specific ICRS artifacts ──────────────────── #

MODEL_FILES = {
    "ranking_model":  "models/ranking_model.pkl",
    "feature_store":  "models/feature_store.pkl",
    "career_gaps":    "data/career_gaps.csv",
    "model_metadata": "data/model_metadata.json",
}


def pull_all_models(output_dir: Path, overwrite: bool = False) -> None:
    """Download all model artifacts from Supabase Storage to output_dir."""
    logger.info("⬇  Pulling model artifacts from Supabase Storage …")
    for key, remote_path in MODEL_FILES.items():
        ext = remote_path.rsplit(".", 1)[-1]
        local_path = output_dir / f"{key.replace('_', '_')}.{ext}"
        # Use the configured settings paths instead of guessing names
        from core.config import settings as cfg
        path_map = {
            "ranking_model":  cfg.RANKING_MODEL_FILE,
            "feature_store":  cfg.FEATURE_STORE_FILE,
            "career_gaps":    cfg.CAREER_GAP_FILE,
            "model_metadata": cfg.MODEL_METADATA_FILE,
        }
        download_file(remote_path, path_map[key], overwrite=overwrite)
    logger.info("⬇  Pull complete.")


def push_all_models(output_dir: Path) -> None:
    """Upload all model artifacts from output_dir to Supabase Storage."""
    logger.info("⬆  Pushing model artifacts to Supabase Storage …")
    from core.config import settings as cfg
    path_map = {
        "ranking_model":  cfg.RANKING_MODEL_FILE,
        "feature_store":  cfg.FEATURE_STORE_FILE,
        "career_gaps":    cfg.CAREER_GAP_FILE,
        "model_metadata": cfg.MODEL_METADATA_FILE,
    }
    for key, remote_path in MODEL_FILES.items():
        upload_file(path_map[key], remote_path)
    logger.info("⬆  Push complete.")
