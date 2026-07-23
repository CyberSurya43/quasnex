"""Confirmation gate for destructive tool actions (file writes, shell exec).

Two kinds of gates:

``confirm(action, detail)``
    Standard pre-action gate: asks the user before a write/edit/delete is
    attempted.  Returns ``True`` to proceed, ``False`` to skip.

``request_os_permission(action, path, reason)``
    Called *after* an OS-level ``PermissionError`` is caught — the tool
    already tried and was denied by the filesystem.  The user is shown what
    happened and asked whether they want the tool to fix the file permissions
    (``chmod u+w``) and retry.  Returns ``True`` to retry, ``False`` to abort.

Both sinks default to *deny* so tools fail safe when no UI is wired in (e.g.
during automated pipeline runs or unit tests).  The chat CLI wires rich
``Confirm.ask`` prompts via ``set_confirmation_sink`` /
``set_os_permission_sink``.  Tests can inject stubs that return True/False.
"""

from __future__ import annotations

from typing import Callable

# ---------------------------------------------------------------------------
# Standard pre-action confirmation
# ---------------------------------------------------------------------------

_sink: Callable[[str, str], bool] | None = None


def set_confirmation_sink(fn: Callable[[str, str], bool] | None) -> None:
    """Register the callback used to ask the user for confirmation.

    The callback receives ``(action, detail)`` and returns ``True`` to proceed.
    """
    global _sink
    _sink = fn


def confirm(action: str, detail: str) -> bool:
    """Ask for confirmation before a destructive action.

    Defaults to auto-deny when no sink is registered, so tools fail safe
    rather than silently acting.
    """
    if _sink is None:
        return False
    return _sink(action, detail)


# ---------------------------------------------------------------------------
# OS-level permission escalation (PermissionError recovery)
# ---------------------------------------------------------------------------

_os_permission_sink: Callable[[str, str, str], bool] | None = None


def set_os_permission_sink(fn: Callable[[str, str, str], bool] | None) -> None:
    """Register the callback used when an OS ``PermissionError`` is caught.

    The callback receives ``(action, path, reason)`` and returns ``True`` if
    the user wants the tool to attempt ``chmod u+w`` and retry the operation.
    """
    global _os_permission_sink
    _os_permission_sink = fn


def request_os_permission(action: str, path: str, reason: str) -> bool:
    """Ask the user whether to fix OS permissions and retry after a ``PermissionError``.

    Returns ``True`` if the user approves the chmod-and-retry, ``False`` to
    abort.  Defaults to deny when no sink is registered.
    """
    if _os_permission_sink is None:
        return False
    return _os_permission_sink(action, path, reason)

