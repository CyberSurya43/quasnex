"""Context command - Manage shared project context."""

from __future__ import annotations

import json
from pathlib import Path

from rich import box
from rich.markup import escape
from rich.syntax import Syntax
from rich.table import Table

from ai_orchestrator.core import context as ctx_store
from ai_orchestrator.cli.ui import console, print_brand_header


def handle_context(args) -> None:
    """Handle the context command."""
    project_dir = args.project_dir.resolve()
    print_brand_header(subtitle="Inspect and shape shared project context")

    if args.ctx_command == "set":
        for pair in args.pairs:
            if "=" not in pair:
                console.print(
                    f"[quasnex.warning]Skipped malformed pair[/quasnex.warning] "
                    f"[quasnex.muted](expected KEY=VALUE): {escape(pair)!r}[/quasnex.muted]"
                )
                continue
            key, _, value = pair.partition("=")
            ctx_store.set_user_preference(project_dir, key.strip(), value.strip())
            console.print(
                f"[quasnex.success]✓ Preference saved[/quasnex.success]  "
                f"[bold]{escape(key.strip())}[/bold] = {escape(value.strip())}"
            )

    elif args.ctx_command == "show":
        data = ctx_store.load(project_dir)
        table = Table(
            box=box.MINIMAL,
            border_style="quasnex.border",
            show_header=False,
            pad_edge=False,
        )
        table.add_column("Project", style="quasnex.muted")
        table.add_column(style="quasnex.path")
        table.add_row("Context store", str(project_dir / ".orchestrator" / "context.json"))
        console.print(table)
        console.print(Syntax(json.dumps(data, indent=2), "json", theme="monokai", word_wrap=True))
