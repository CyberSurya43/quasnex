"""Initialize command - Create a new orchestration project."""

from __future__ import annotations

from pathlib import Path

from ...scaffolding import init_project


def handle_init(project_dir: Path, name: str | None, force: bool) -> None:
    """Handle the init command."""
    init_project(project_dir, name, force)
    print(f"Created orchestrator project at {project_dir.resolve()}")
