"""
api/views.py — Django REST API views for the ICRS backend.

Design decisions:
  - Data is loaded lazily on first request (not at module import time), so
    `manage.py migrate`, `collectstatic`, and test collection all work without
    a live database.
  - A thread-safe double-checked locking pattern ensures data is loaded exactly
    once, even under concurrent first requests.
  - Input validation added: muid length, JSON parse guard, role guard.
  - Structured logging replaces all print() statements.
  - @csrf_exempt removed; the API is protected via CORS allowlist in settings.
"""
import json
import logging
import threading
from pathlib import Path
import sys

import pandas as pd
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

# Path bootstrap so Django can find the core module
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

logger = logging.getLogger(__name__)

# ── Lazy, thread-safe data cache ──────────────────────────────────────────── #
# All data lives here once loaded; never re-loaded while the server runs.
# Access is protected by _LOCK to handle concurrent first requests safely.

_LOCK = threading.Lock()
_CACHE: dict = {}


def _ensure_data_loaded() -> tuple:
    """
    Load and cache user_data, task_data, and task_features_cache.
    Thread-safe via double-checked locking.
    Returns (user_data, task_data, task_features_cache) or raises on failure.
    """
    if 'user_data' not in _CACHE:
        with _LOCK:
            # Second check inside lock (double-checked locking pattern)
            if 'user_data' not in _CACHE:
                logger.info("Loading data from database (first request)…")
                from core.loader import DataLoader
                from core.ranking import engineer_task_features

                user_data, task_data, _ = DataLoader().load_all()
                logger.info("Pre-computing task features (TF-IDF + popularity)…")
                task_features_cache = engineer_task_features(user_data, task_data)
                logger.info(f"Task features ready: {len(task_features_cache)} tasks.")

                _CACHE['user_data'] = user_data
                _CACHE['task_data'] = task_data
                _CACHE['task_features'] = task_features_cache

    return _CACHE['user_data'], _CACHE['task_data'], _CACHE['task_features']


# ── API Views ─────────────────────────────────────────────────────────────── #

@require_http_methods(["POST"])
def api_generate_roadmap(request):
    """
    POST /generate_roadmap
    Body: { "muid": str, "name": str (optional), "role": str }
    Returns a full personalised career roadmap.
    """
    # ── Parse body ────────────────────────────────────────────────────────── #
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        logger.warning(f"Invalid JSON body: {exc}")
        return JsonResponse({"detail": "Request body must be valid JSON."}, status=400)

    # ── Validate inputs ───────────────────────────────────────────────────── #
    muid = str(body.get('muid', '')).strip()
    name = str(body.get('name', '')).strip()
    role = str(body.get('role', '')).strip()

    if not muid:
        return JsonResponse({"detail": "muid is required."}, status=400)
    if len(muid) > 200:
        return JsonResponse({"detail": "muid must be 200 characters or fewer."}, status=400)
    if len(name) > 200:
        return JsonResponse({"detail": "name must be 200 characters or fewer."}, status=400)
    if len(role) > 200:
        return JsonResponse({"detail": "role must be 200 characters or fewer."}, status=400)

    if not name:
        # Derive a sensible display name from the MUID
        name = muid.split('@')[0].capitalize()

    # ── Load data (lazy) ──────────────────────────────────────────────────── #
    try:
        user_data, task_data, task_features_cache = _ensure_data_loaded()
    except Exception:
        logger.exception("Data loading failed")
        return JsonResponse(
            {"detail": "Service unavailable: could not load data. Please try again later."},
            status=503,
        )

    # ── Generate roadmap ─────────────────────────────────────────────────── #
    try:
        from core.pipeline import generate_roadmap

        result = generate_roadmap(
            muid, name, role,
            user_data, task_data,
            task_features=task_features_cache,
        )
    except Exception:
        logger.exception(f"Roadmap generation failed for muid={muid!r}")
        return JsonResponse(
            {"detail": "Internal error during roadmap generation."},
            status=500,
        )

    # ── Serialize response ───────────────────────────────────────────────── #
    gap_data = result.get("gap", {})

    recs_df = result.get("recs")
    recs_data = []
    if isinstance(recs_df, pd.DataFrame) and not recs_df.empty:
        recs_data = recs_df.head(10).to_dict(orient="records")

    roadmap = result.get("roadmap", {})

    logger.info(
        f"Roadmap generated | muid={muid!r} | role={result.get('role')!r} | "
        f"known_user={result.get('known_user')} | "
        f"readiness={gap_data.get('readiness_pct', 0):.1f}%"
    )

    return JsonResponse({
        "success": True,
        "muid": muid,
        "name": name,
        "role": result.get("role", role),   # may have been normalized by pipeline
        "gap": gap_data,
        "recs": recs_data,
        "roadmap": roadmap,
        "known_user": result.get("known_user", False),
        "submitted_tasks": result.get("submitted_tasks", []),
    })
