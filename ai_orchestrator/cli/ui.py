"""Shared Quasnex CLI branding and Rich presentation helpers."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from rich.console import Console
from rich.live import Live
from rich.rule import Rule
from rich.spinner import Spinner
from rich.text import Text
from rich.theme import Theme


APP_NAME = "Quasnex"
BRAND_ICON = "[Q]"
TAGLINE = "Multi-Model AI Coding Orchestrator"

QUASNEX_THEME = Theme(
    {
        "quasnex.brand": "bold #e2e8f0",
        "quasnex.accent": "bold #22d3ee",
        "quasnex.violet": "bold #a78bfa",
        "quasnex.muted": "#64748b",
        "quasnex.subtle": "#94a3b8",
        "quasnex.border": "#334155",
        "quasnex.success": "bold #34d399",
        "quasnex.warning": "bold #fbbf24",
        "quasnex.error": "bold #fb7185",
        "quasnex.path": "#67e8f9 underline",
    }
)

console = Console(theme=QUASNEX_THEME, highlight=False)


def brand_lockup() -> Text:
    """Return the compact Quasnex wordmark used throughout the CLI."""
    return Text.assemble(
        (BRAND_ICON, "quasnex.accent"),
        (f"  {APP_NAME}", "quasnex.brand"),
        (f" — {TAGLINE}", "quasnex.muted"),
    )


def metadata_chip(label: str, value: str, *, accent: str = "#22d3ee") -> Text:
    """Build a compact label/value chip suitable for status dashboards."""
    chip = Text()
    chip.append(f" {label.upper()} ", style=f"bold #0b1120 on {accent}")
    chip.append(f" {value} ", style="#cbd5e1 on #1e293b")
    return chip


def print_brand_header(*, subtitle: str | None = None) -> None:
    """Render a clean, low-noise branded header for one-shot commands."""
    console.print()
    console.print(Rule(brand_lockup(), style="quasnex.border", align="left"))
    console.print(Text(f"  {subtitle or TAGLINE}", style="quasnex.subtle"))
    console.print()


def quasnex_activity(message: str) -> Live:
    """Pulse between connected nodes without implying measured task progress."""
    spinner = Spinner(
        "dots",
        text=Text.assemble(
            (f"{APP_NAME}  ", "quasnex.brand"),
            (message, "quasnex.subtle"),
        ),
        style="quasnex.accent",
    )
    spinner.frames = [
        "[Q] ●──○──○", "[Q] ○●─○──○", "[Q] ○─●○──○",
        "[Q] ○──●──○", "[Q] ○──○●─○", "[Q] ○──○─●○",
        "[Q] ○──○──●", "[Q] ○──○──○",
    ]
    spinner.interval = 140
    return Live(spinner, console=console, refresh_per_second=10, transient=True)


@contextmanager
def quasnex_indexing_animation() -> Iterator[Live]:
    """Show Quasnex activity while building repository context."""
    with quasnex_activity("Indexing repository · building code context") as status:
        yield status
