"""Initialize command - Create a new orchestration project."""

from __future__ import annotations

from pathlib import Path

from rich.text import Text

from ... import knowledge_graph as kg
from ...scaffolding import init_project
from ..ui import console, print_brand_header


def handle_init(project_dir: Path, name: str | None, force: bool) -> None:
    """Handle the init command."""
    print_brand_header(subtitle="Create a new engineering workspace")
    with console.status(
        "[quasnex.subtle]Scaffolding workspace[/quasnex.subtle]",
        spinner="arc",
        spinner_style="quasnex.violet",
    ):
        init_project(project_dir, name, force)
        graph = kg.build_or_update(project_dir.resolve() / "workspace", project_dir.resolve())
    console.print("[quasnex.success]✓ Project ready[/quasnex.success] ", end="")
    console.print(Text(str(project_dir.resolve()), style="quasnex.path"))
    console.print(
        f"[quasnex.muted]Indexed {len(graph['files'])} files and "
        f"{len(graph['edges'])} import edges.[/quasnex.muted]"
    )
