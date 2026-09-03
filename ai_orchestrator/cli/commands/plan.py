"""Plan command - Generate task packets for every stage."""

from __future__ import annotations

from pathlib import Path

from rich.text import Text

from ai_orchestrator.core import Orchestrator
from ai_orchestrator.cli.ui import console, print_brand_header


def handle_plan(project_dir: Path) -> None:
    """Handle the plan command."""
    print_brand_header(subtitle="Turn the roadmap into executable stages")
    orchestrator = Orchestrator(project_dir)
    with console.status("[forge.muted]Generating stage plans...[/forge.muted]", spinner="dots"):
        run_dir = orchestrator.plan()
    console.print("[forge.success]✓ Plan generated[/forge.success] ", end="")
    console.print(Text(str(run_dir), style="forge.path"))
