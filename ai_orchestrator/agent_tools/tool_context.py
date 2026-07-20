"""Shared per-agent tool state."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ToolContext:
    """Tracks lightweight workflow state across tools in one agent session."""
    kg_resolved: bool = False
    last_resolve_description: str | None = None
    edit_failures: dict[str, int] = field(default_factory=dict)
    edit_attempts: dict[str, int] = field(default_factory=dict)
