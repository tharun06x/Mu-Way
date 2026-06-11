from career_roadmap.ui import run_console_app


def test_ui_entrypoint_is_callable():
    assert callable(run_console_app)
