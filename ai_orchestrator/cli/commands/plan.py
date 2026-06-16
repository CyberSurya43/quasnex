"""Plan command - Generate task packets for every stage."""

from __future__ import annotations

from pathlib import Path

from ai_orchestrator.core import Orchestrator


def handle_plan(project_dir: Path) -> None:
    """Handle the plan command."""
    orchestrator = Orchestrator(project_dir)
    run_dir = orchestrator.plan()
    print(f"Generated orchestration plan at {run_dir}")
