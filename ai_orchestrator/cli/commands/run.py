"""Run command - Dry-run or execute configured agent commands."""

from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.prompt import Confirm

from ai_orchestrator.agent_tools import set_confirmation_sink
from ai_orchestrator.core import Orchestrator

console = Console()


def _confirm_sink(action: str, detail: str) -> bool:
    return Confirm.ask(f"[yellow]Allow[/yellow] {action}: [bold]{detail}[/bold]?", default=False)


def handle_run(args) -> None:
    """Handle the run command."""
    set_confirmation_sink(_confirm_sink)
    orchestrator = Orchestrator(args.project_dir)
    results = orchestrator.run(args.stage, args.execute)

    for result in results:
        mode = "executed" if result["executed"] else "dry-run"
        provider = result.get("provider_used") or "n/a"
        status = "ok" if result.get("success") else ("pending" if not result["executed"] else "FAILED")
        print(f"[{mode}] {result['stage']} -> {result['agent']} (provider: {provider}, status: {status})")
        print(f"  task: {result['task_file']}")
