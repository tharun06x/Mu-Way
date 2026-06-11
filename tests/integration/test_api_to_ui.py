from career_roadmap.api import create_app
from career_roadmap.ui import run_console_app


def test_api_to_ui_import_handoff():
    assert create_app() is not None
    assert callable(run_console_app)
