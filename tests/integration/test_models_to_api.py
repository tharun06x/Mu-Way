from career_roadmap.api import create_app


def test_models_to_api_health_handoff():
    app = create_app()
    assert app.test_client().get("/api/health").status_code == 200
