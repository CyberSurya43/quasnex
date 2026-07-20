"""Initialize command - Create a new orchestration project."""

from __future__ import annotations

from pathlib import Path

from ... import knowledge_graph as kg
from ...scaffolding import init_project


def handle_init(project_dir: Path, name: str | None, force: bool) -> None:
    """Handle the init command."""
    init_project(project_dir, name, force)
    kg.build_or_update(project_dir.resolve() / "workspace", project_dir.resolve())
    print(f"Created orchestrator project at {project_dir.resolve()}")
