"""Console UI entry points."""

from __future__ import annotations

from .utils import ensure_project_root_on_path


def run_console_app():
    """Run the existing interactive roadmap console app."""
    ensure_project_root_on_path()
    from roadmap_app import main

    main()


if __name__ == "__main__":
    run_console_app()
