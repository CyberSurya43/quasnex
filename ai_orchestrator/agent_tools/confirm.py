"""Confirmation gate for destructive tool actions (file writes, shell exec).

Tool modules stay UI-agnostic: they call ``confirm(...)`` and get a bool back.
The chat/run CLI wires in a ``rich``-based confirmation prompt via
``set_confirmation_sink``; tests can inject a stub that always returns True/False.
"""

from __future__ import annotations

from typing import Callable

_sink: Callable[[str, str], bool] | None = None


def set_confirmation_sink(fn: Callable[[str, str], bool] | None) -> None:
    """Register the callback used to ask the user for confirmation.

    The callback receives (action, detail) and returns True to proceed.
    """
    global _sink
    _sink = fn


def confirm(action: str, detail: str) -> bool:
    """Ask for confirmation before a destructive action. Defaults to auto-deny
    when no sink is registered, so tools fail safe rather than silently acting.
    """
    if _sink is None:
        return False
    return _sink(action, detail)
