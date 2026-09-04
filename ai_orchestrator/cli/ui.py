"""Shared Cosnex CLI branding and Rich presentation helpers."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from rich.console import Console
from rich.rule import Rule
from rich.status import Status
from rich.text import Text
from rich.theme import Theme


APP_NAME = "Cosnex"
BRAND_ICON = "◉─✦─◉"
TAGLINE = "Navigate the code cosmos. Connect every nexus."

COSNEX_THEME = Theme(
    {
        "cosnex.brand": "bold #e2e8f0",
        "cosnex.accent": "bold #22d3ee",
        "cosnex.violet": "bold #a78bfa",
        "cosnex.muted": "#64748b",
        "cosnex.subtle": "#94a3b8",
        "cosnex.border": "#334155",
        "cosnex.success": "bold #34d399",
        "cosnex.warning": "bold #fbbf24",
        "cosnex.error": "bold #fb7185",
        "cosnex.path": "#67e8f9 underline",
    }
)

console = Console(theme=COSNEX_THEME, highlight=False)


def brand_lockup() -> Text:
    """Return the compact Cosnex wordmark used throughout the CLI."""
    return Text.assemble(
        (BRAND_ICON, "cosnex.accent"),
        ("  COSNEX", "cosnex.brand"),
        ("  /  AI engineering workspace", "cosnex.muted"),
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
    console.print(Rule(brand_lockup(), style="cosnex.border", align="left"))
    console.print(Text(f"  {subtitle or TAGLINE}", style="cosnex.subtle"))
    console.print()


@contextmanager
def cosnex_indexing_animation() -> Iterator[Status]:
    """Animate a small cosmos-to-nexus sequence while repository indexing runs."""
    message = (
        f"[cosnex.brand]{BRAND_ICON}[/cosnex.brand] "
        "[cosnex.accent]Mapping the code cosmos[/cosnex.accent] "
        "[cosnex.muted]• linking the nexus...[/cosnex.muted]"
    )
    with console.status(
        message,
        spinner="moon",
        spinner_style="cosnex.accent",
        refresh_per_second=12.0,
    ) as status:
        yield status
