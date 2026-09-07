"""Run command - Dry-run or execute configured agent commands."""

from __future__ import annotations

from rich import box
from rich.prompt import Confirm
from rich.table import Table

from ai_orchestrator.agent_tools import set_confirmation_sink
from ai_orchestrator.core import Orchestrator
from ai_orchestrator.cli.ui import console, print_brand_header


def _confirm_sink(action: str, detail: str) -> bool:
    return Confirm.ask(f"[yellow]Allow[/yellow] {action}: [bold]{detail}[/bold]?", default=False)


def handle_run(args) -> None:
    """Handle the run command."""
    print_brand_header(subtitle="Execute the configured delivery pipeline")
    set_confirmation_sink(_confirm_sink)
    orchestrator = Orchestrator(args.project_dir)
    results = orchestrator.run(args.stage, args.execute)

    table = Table(
        title="PIPELINE RESULTS",
        title_style="quasnex.brand",
        box=box.SIMPLE_HEAVY,
        border_style="quasnex.border",
        header_style="quasnex.muted",
        row_styles=("", "#cbd5e1"),
        pad_edge=False,
    )
    table.add_column("Mode", style="quasnex.muted")
    table.add_column("Stage", style="bold")
    table.add_column("Agent")
    table.add_column("Model", overflow="fold")
    table.add_column("Status", justify="center")
    table.add_column("Task file", style="quasnex.path", overflow="fold")
    for result in results:
        mode = "executed" if result["executed"] else "dry-run"
        model = result.get("model_used") or "n/a"
        status = (
            "[quasnex.success]✓ passed[/quasnex.success]"
            if result.get("success")
            else (
                "[quasnex.warning]● pending[/quasnex.warning]"
                if not result["executed"]
                else "[quasnex.error]✗ failed[/quasnex.error]"
            )
        )
        table.add_row(
            mode,
            str(result["stage"]),
            str(result["agent"]),
            str(model),
            status,
            str(result["task_file"]),
        )
    console.print(table)
