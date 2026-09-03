"""Shared ForgeFlow CLI branding and Rich presentation helpers."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.theme import Theme


APP_NAME = "ForgeFlow"
TAGLINE = "Plan. Build. Verify. Ship."

FORGEFLOW_THEME = Theme(
    {
        "forge.brand": "bold bright_cyan",
        "forge.accent": "bright_magenta",
        "forge.muted": "grey62",
        "forge.success": "bold green",
        "forge.warning": "bold yellow",
        "forge.error": "bold red",
        "forge.path": "cyan underline",
    }
)

console = Console(theme=FORGEFLOW_THEME)


def print_brand_header(*, subtitle: str | None = None) -> None:
    """Render a compact branded header for one-shot CLI commands."""
    title = Text(APP_NAME, style="forge.brand", justify="center")
    body = Text(subtitle or TAGLINE, style="forge.muted", justify="center")
    console.print(
        Panel(
            body,
            title=title,
            subtitle="AI engineering workspace",
            border_style="bright_cyan",
            padding=(0, 2),
        )
    )
