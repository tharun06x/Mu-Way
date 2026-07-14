import logging
import sys
from pathlib import Path
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class ApiConfig(AppConfig):
    name = 'api'

    def ready(self):
        """
        Called once when Django starts up.
        Pulls ML model artifacts from Supabase Storage if they are missing locally.
        This ensures the app always has up-to-date models even on a fresh deploy.
        """
        # Only run in the main process (not the auto-reloader child)
        if 'runserver' in sys.argv and '--noreload' not in sys.argv:
            import os
            if os.environ.get('RUN_MAIN') != 'true':
                return

        try:
            # Import here to avoid circular imports at module load time
            ROOT = Path(__file__).resolve().parent.parent
            if str(ROOT) not in sys.path:
                sys.path.insert(0, str(ROOT))

            from core.config import settings as cfg
            from core import storage

            output_dir = cfg.OUTPUT_DIR
            missing = any([
                not cfg.RANKING_MODEL_FILE.exists(),
                not cfg.FEATURE_STORE_FILE.exists(),
            ])

            if missing:
                logger.info("🔄 Model files missing locally — pulling from Supabase Storage …")
                storage.pull_all_models(output_dir)
            else:
                logger.info("✓ Model files already present locally.")

        except EnvironmentError as e:
            logger.warning(f"Supabase Storage not configured: {e}")
            logger.warning("  → Running with local model files only.")
        except Exception as e:
            logger.warning(f"Could not pull models from Supabase Storage: {e}")
            logger.warning("  → Continuing with local model files.")
