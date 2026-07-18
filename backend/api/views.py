"""
api/views.py — Django REST API views for the ICRS backend.

Design decisions:
  - Data is loaded lazily on first request (not at module import time).
  - A thread-safe double-checked locking pattern ensures data is loaded once.
  - Input validation added: muid length, JSON parse guard, role guard.
  - Structured logging replaces all print() statements.
  - New endpoints: /compare_roles, /insights
  - Roadmap persistence: generated roadmaps are saved to UserRoadmap.
    Subsequent calls return the cached roadmap without running the ML pipeline.
    Pass regenerate=true to force a fresh generation (deletes the old roadmap).
"""
import json
import logging
import threading
from pathlib import Path
import sys

import pandas as pd
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

# Path bootstrap so Django can find the core module
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

logger = logging.getLogger(__name__)

# ── Lazy, thread-safe data cache ──────────────────────────────────────────── #
_LOCK = threading.Lock()
_CACHE: dict = {}


def _ensure_data_loaded() -> tuple:
    """Thread-safe lazy data loader. Loads once, cached forever."""
    if 'user_data' not in _CACHE:
        with _LOCK:
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


def _parse_json_body(request) -> tuple[dict | None, JsonResponse | None]:
    """Parse and return JSON body, or return (None, error_response)."""
    try:
        return json.loads(request.body), None
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        logger.warning(f"Invalid JSON body: {exc}")
        return None, JsonResponse({"detail": "Request body must be valid JSON."}, status=400)


# ── Main Roadmap Endpoint ─────────────────────────────────────────────────── #

@csrf_exempt
@require_http_methods(["POST"])
def api_generate_roadmap(request):
    """
    POST /generate_roadmap
    Body: {
        "muid": str,
        "name": str (optional),
        "role": str,
        "enable_decay": bool (optional, default true),
        "enrich_tasks": bool (optional, default true),
        "regenerate": bool (optional, default false)
    }

    Behaviour:
      - If a saved roadmap exists in DB and regenerate=false → return it instantly.
      - If regenerate=true → delete old roadmap, run full ML pipeline, save new one.
      - On first generation → run ML pipeline and save to DB.
    """
    body, err = _parse_json_body(request)
    if err:
        return err

    muid       = str(body.get('muid', '')).strip()
    name       = str(body.get('name', '')).strip()
    role       = str(body.get('role', '')).strip()
    enable_decay = body.get('enable_decay', True)
    enrich       = body.get('enrich_tasks', True)
    regenerate   = bool(body.get('regenerate', False))

    if not muid:
        return JsonResponse({"detail": "muid is required."}, status=400)
    if len(muid) > 200:
        return JsonResponse({"detail": "muid must be 200 characters or fewer."}, status=400)
    if len(name) > 200:
        return JsonResponse({"detail": "name must be 200 characters or fewer."}, status=400)
    if len(role) > 200:
        return JsonResponse({"detail": "role must be 200 characters or fewer."}, status=400)

    if not name:
        name = muid.split('@')[0].capitalize()

    # ── Roadmap Persistence: Cache Check ──────────────────────────────────── #
    from api.models import UserRoadmap

    if not regenerate:
        try:
            saved = UserRoadmap.objects.filter(user_id=muid, role=role).first()
            if saved:
                logger.info(f"Returning cached roadmap | muid={muid!r} | role={role!r}")
                cached_payload = saved.roadmap_data
                # Inject the current name in case it changed
                cached_payload['name'] = name
                cached_payload['from_cache'] = True
                return JsonResponse(cached_payload)
        except Exception as exc:
            logger.warning(f"Cache lookup failed (non-fatal, will regenerate): {exc}")

    # ── If regenerate=True, delete the old roadmap first ─────────────────── #
    if regenerate:
        try:
            deleted_count, _ = UserRoadmap.objects.filter(user_id=muid, role=role).delete()
            if deleted_count:
                logger.info(f"Deleted old roadmap | muid={muid!r} | role={role!r}")
        except Exception as exc:
            logger.warning(f"Failed to delete old roadmap (non-fatal): {exc}")

    # ── Load in-memory data (with thread-safe lazy load) ──────────────────── #
    try:
        user_data, task_data, task_features_cache = _ensure_data_loaded()
    except Exception:
        logger.exception("Data loading failed")
        return JsonResponse({"detail": "Service unavailable — data loading failed."}, status=503)

    # ── Run the ML Pipeline ───────────────────────────────────────────────── #
    try:
        from core.pipeline import generate_roadmap

        result = generate_roadmap(
            muid, name, role,
            user_data, task_data,
            task_features=task_features_cache,
        )
    except Exception:
        logger.exception(f"Roadmap generation failed for muid={muid!r}")
        return JsonResponse({"detail": "Internal error during roadmap generation."}, status=500)

    # ── Enrich roadmap tasks with learning resources ──────────────────────── #
    roadmap = result.get("roadmap", {})
    if enrich and roadmap and roadmap.get('roadmap_weeks'):
        try:
            from core.services.enrichment_service import enrich_roadmap_weeks
            roadmap['roadmap_weeks'] = enrich_roadmap_weeks(roadmap['roadmap_weeks'])
        except Exception as exc:
            logger.warning(f"Task enrichment failed (non-fatal): {exc}")

    # ── Skill Decay Profile ───────────────────────────────────────────────── #
    decay_profile = None
    if enable_decay:
        try:
            from core.ml.decay import apply_decay_to_features
            from core.features import compute_user_features
            user_subs = user_data[user_data['user_id'] == muid].copy() if not user_data.empty else pd.DataFrame()
            if not user_subs.empty:
                user_feats = compute_user_features(muid, user_subs, pd.Timestamp.now())
                _, profile = apply_decay_to_features(user_feats, user_subs)
                decay_profile = profile.to_dict()
        except Exception as exc:
            logger.warning(f"Decay profile computation failed (non-fatal): {exc}")

    # ── Progress Forecast ─────────────────────────────────────────────────── #
    forecast = None
    try:
        from core.ml.forecaster import compute_progress_forecast, AdaptiveGoalEngine
        gap_data = result.get("gap", {})
        user_subs_for_forecast = user_data[user_data['user_id'] == muid].copy() if not user_data.empty else pd.DataFrame()
        forecast_obj = compute_progress_forecast(muid, gap_data, user_subs_for_forecast)
        forecast = forecast_obj.to_dict()

        goal_engine = AdaptiveGoalEngine()
        adaptive_goal = goal_engine.compute_goal(
            user_subs_for_forecast,
            gap_data.get('career_gap_tier', 'MODERATE'),
        )
        forecast['adaptive_goal'] = adaptive_goal.to_dict()
    except Exception as exc:
        logger.warning(f"Forecast computation failed (non-fatal): {exc}")

    # ── Achievement Profile ───────────────────────────────────────────────── #
    achievements = None
    try:
        from core.services.achievements_service import compute_achievements
        user_subs_achv = user_data[user_data['user_id'] == muid].copy() if not user_data.empty else pd.DataFrame()
        achv_profile = compute_achievements(muid, user_subs_achv)
        achievements = achv_profile.to_dict()
    except Exception as exc:
        logger.warning(f"Achievement computation failed (non-fatal): {exc}")

    # ── Serialize Response ────────────────────────────────────────────────── #
    gap_data = result.get("gap", {})
    recs_df = result.get("recs")
    recs_data = []
    if isinstance(recs_df, pd.DataFrame) and not recs_df.empty:
        recs_data = recs_df.head(10).to_dict(orient="records")

    logger.info(
        f"Roadmap generated | muid={muid!r} | role={result.get('role')!r} | "
        f"known_user={result.get('known_user')} | "
        f"readiness={gap_data.get('readiness_pct', 0):.1f}%"
    )

    response_payload = {
        "success":         True,
        "muid":            muid,
        "name":            name,
        "role":            result.get("role", role),
        "gap":             gap_data,
        "recs":            recs_data,
        "roadmap":         roadmap,
        "known_user":      result.get("known_user", False),
        "submitted_tasks": result.get("submitted_tasks", []),
        "forecast":        forecast,
        "achievements":    achievements,
        "decay_profile":   decay_profile,
        "from_cache":      False,
    }

    # ── Persist Roadmap to DB ─────────────────────────────────────────────── #
    # Normalise role before saving (pipeline may have corrected it)
    saved_role = result.get("role", role)
    try:
        UserRoadmap.objects.update_or_create(
            user_id=muid,
            role=saved_role,
            defaults={"roadmap_data": response_payload},
        )
        logger.info(f"Roadmap saved to DB | muid={muid!r} | role={saved_role!r}")
    except Exception as exc:
        logger.warning(f"Failed to save roadmap to DB (non-fatal): {exc}")

    return JsonResponse(response_payload)


# ── Multi-Role Comparison Endpoint ────────────────────────────────────────── #

@csrf_exempt
@require_http_methods(["POST"])
def api_compare_roles(request):
    """
    POST /compare_roles
    Body: { "muid": str, "role_a": str, "role_b": str }
    Returns side-by-side gap analysis, forecasts, and a recommendation.
    """
    body, err = _parse_json_body(request)
    if err:
        return err

    muid   = str(body.get('muid', '')).strip()
    role_a = str(body.get('role_a', '')).strip()
    role_b = str(body.get('role_b', '')).strip()

    if not muid or not role_a or not role_b:
        return JsonResponse({"detail": "muid, role_a, and role_b are required."}, status=400)
    if role_a == role_b:
        return JsonResponse({"detail": "role_a and role_b must be different."}, status=400)

    try:
        user_data, task_data, _ = _ensure_data_loaded()
    except Exception:
        return JsonResponse({"detail": "Service unavailable."}, status=503)

    try:
        from core.features import compute_user_features
        from core.ml.forecaster import compare_roles
        from core.config import settings as _cfg

        user_subs = user_data[user_data['user_id'] == muid].copy() if not user_data.empty else pd.DataFrame()
        user_feats = compute_user_features(muid, user_subs, pd.Timestamp.now())
        user_mastery = {
            dom: float(user_feats.get(f'mastery_{dom}', 0.0))
            for dom in _cfg.DOMAINS
        }

        comparison = compare_roles(muid, user_mastery, role_a, role_b, user_subs)
        return JsonResponse({"success": True, "comparison": comparison.to_dict()})

    except Exception:
        logger.exception(f"Role comparison failed for muid={muid!r}")
        return JsonResponse({"detail": "Internal error during role comparison."}, status=500)


# ── Insights / Achievements Endpoint ─────────────────────────────────────── #

@csrf_exempt
@require_http_methods(["POST"])
def api_insights(request):
    """
    POST /insights
    Body: { "muid": str }
    Returns the user's achievement profile, streak, XP, and badges.
    """
    body, err = _parse_json_body(request)
    if err:
        return err

    muid = str(body.get('muid', '')).strip()
    if not muid:
        return JsonResponse({"detail": "muid is required."}, status=400)

    try:
        user_data, _, _ = _ensure_data_loaded()
    except Exception:
        return JsonResponse({"detail": "Service unavailable."}, status=503)

    try:
        from core.services.achievements_service import compute_achievements
        user_subs = user_data[user_data['user_id'] == muid].copy() if not user_data.empty else pd.DataFrame()
        profile = compute_achievements(muid, user_subs)
        return JsonResponse({"success": True, "achievements": profile.to_dict()})
    except Exception:
        logger.exception(f"Insights failed for muid={muid!r}")
        return JsonResponse({"detail": "Internal error computing insights."}, status=500)
