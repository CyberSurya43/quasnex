"""Run command - Dry-run or execute configured agent commands."""

from __future__ import annotations

from pathlib import Path

from ai_orchestrator.core import Orchestrator


def handle_run(args) -> None:
    """Handle the run command."""
    orchestrator = Orchestrator(args.project_dir)
    results = orchestrator.run(args.stage, args.execute)
    
    for result in results:
        mode = "executed" if result["executed"] else "dry-run"
        model = result.get("model_used") or "n/a"
        print(f"[{mode}] {result['stage']} -> {result['agent']} (model: {model})")
        print(f"  task: {result['task_file']}")
        print(f"  cmd:  {result['command']}")
