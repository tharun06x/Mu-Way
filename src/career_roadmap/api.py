"""REST API for user profiles and recommendations."""

from __future__ import annotations

import argparse

from .utils import ensure_project_root_on_path


# ── Module-level data cache (B23 fix) ─────────────────────────────────────── #
# Load data once at startup instead of on every request (was 5-30s per call).
_DATA_CACHE: dict = {}


def _get_data():
    """Return cached (user_data, task_data) loading from disk only once."""
    if not _DATA_CACHE:
        ensure_project_root_on_path()
        from data_loader import DataLoader
        user_data, task_data, _ = DataLoader().load_all()
        _DATA_CACHE['user_data'] = user_data
        _DATA_CACHE['task_data'] = task_data
    return _DATA_CACHE['user_data'], _DATA_CACHE['task_data']


def create_app():
    """Create the Flask API app."""
    try:
        from flask import Flask, jsonify, request
    except ImportError as exc:
        raise RuntimeError("Flask is required for the API. Install requirements.txt.") from exc

    ensure_project_root_on_path()
    import pandas as pd
    from problem1 import compute_user_features, hashtag_to_domain
    from roadmap_app import generate_roadmap

    app = Flask(__name__)

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"})

    @app.get("/api/user/<user_id>")
    def user_profile(user_id: str):
        user_data, task_data = _get_data()
        rows = user_data[user_data["user_id"] == user_id].copy()
        if len(rows) == 0:
            return jsonify({"user_id": user_id, "known_user": False}), 404

        # B24 fix: compute_user_features(user_id, user_data, ref) — no task_data kwarg.
        # Pre-process rows the same way roadmap_app.generate_roadmap() does.
        rows["domain_mapped"] = rows["domain"].apply(hashtag_to_domain)
        if "difficulty_level" not in rows.columns:
            dmap = task_data.set_index("task_name")["difficulty_level"].to_dict()
            rows["difficulty_level"] = rows["task_name"].map(dmap).fillna(2.0).astype(float)

        features = compute_user_features(user_id, rows, ref=pd.Timestamp.now())
        # Convert numpy types to Python native for JSON serialisation
        features_serialisable = {k: (int(v) if hasattr(v, 'item') else v)
                                  for k, v in features.items() if k != 'user_id'}
        return jsonify({"user_id": user_id, "known_user": True, "features": features_serialisable})

    @app.post("/api/rank/<user_id>")
    def rank(user_id: str):
        payload = request.get_json(silent=True) or {}
        role = payload.get("role", "Full Stack Developer")
        name = payload.get("name", user_id.split("@")[0].capitalize())
        user_data, task_data = _get_data()
        result = generate_roadmap(user_id, name, role, user_data, task_data)
        recs = result["recs"].head(int(payload.get("top_k", 5))).to_dict(orient="records")
        return jsonify({
            "user_id": user_id,
            "role": role,
            "known_user": result["known_user"],
            "career_gap": result["gap"]["career_gap"],
            "readiness_pct": result["gap"]["readiness_pct"],
            "recommendations": recs,
            "roadmap": result["roadmap"],
        })

    return app


def main():
    parser = argparse.ArgumentParser(description="Mulearn Career Roadmap API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()
    create_app().run(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
