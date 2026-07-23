"""Filesystem tools for the coding agent, scoped to a workspace root.

Reads are unrestricted. Writes/edits require confirmation (see ``confirm.py``)
and are always resolved relative to, and confined within, the workspace root
so the agent can't wander outside the project directory.
"""

from __future__ import annotations

from pathlib import Path

from langchain_core.tools import BaseTool, tool

from .confirm import confirm, request_os_permission
from .tool_context import ToolContext

_IGNORE_DIRS = {
    ".git", ".orchestrator", ".venv", "venv", "node_modules", "__pycache__",
    ".pytest_cache", ".mypy_cache", "dist", "build", ".next", ".cache", "egg-info",
}
_MAX_READ_CHARS = 20_000
_MAX_TREE_ENTRIES = 400
_KG_FIRST_WARNING = (
    "KG-FIRST WARNING: call resolve_issue(description) before reading/listing/searching "
    "project files for a task. Continue only if this is an exact user-specified path "
    "or KG results were empty/unhelpful.\n\n"
)
_MAX_EDIT_FAILURES_PER_FILE = 2
_MAX_EDIT_ATTEMPTS_PER_FILE = 3


class WorkspaceEscapeError(ValueError):
    pass


def _resolve(workspace_root: Path, relative_path: str) -> Path:
    candidate = (workspace_root / relative_path).resolve()
    workspace_root = workspace_root.resolve()
    if candidate != workspace_root and workspace_root not in candidate.parents:
        raise WorkspaceEscapeError(f"{relative_path!r} escapes the workspace root")
    return candidate


def _is_ignored(path: Path) -> bool:
    return any(part in _IGNORE_DIRS for part in path.parts)


def build_tools(workspace_root: Path, context: ToolContext | None = None) -> list[BaseTool]:
    workspace_root = workspace_root.resolve()
    workspace_root.mkdir(parents=True, exist_ok=True)
    context = context or ToolContext()

    def _fix_and_retry(action: str, path: Path, write_fn):
        """Run write_fn(); if a PermissionError is raised, ask the user whether
        to chmod u+w and retry once.  Returns the result string."""
        try:
            return write_fn()
        except PermissionError as exc:
            rel = str(path.relative_to(workspace_root))
            reason = str(exc)
            if request_os_permission(action, rel, reason):
                try:
                    path.chmod(path.stat().st_mode | 0o200)  # add owner-write bit
                except OSError as chmod_exc:
                    return (
                        f"Error: could not fix permissions on {rel}: {chmod_exc}. "
                        "Resolve the file permissions manually and try again."
                    )
                try:
                    return write_fn()  # retry after chmod
                except PermissionError as exc2:
                    return (
                        f"Error: still cannot {action} {rel} after chmod: {exc2}. "
                        "Check that the parent directory is also writable."
                    )
            return (
                f"Skipped {action} on {rel}: user declined to grant write permission. "
                "The file was not modified."
            )

    def kg_warning() -> str:
        return "" if context.kg_resolved else _KG_FIRST_WARNING

    def permission_declined(action: str, path: str) -> str:
        # Deliberately NOT a "HARD STOP" — a single declined confirmation should
        # not abort the whole agent turn (see run_shell's graceful decline for
        # the same pattern). The agent should move on to other work or ask the
        # user, not repeat the exact same write/edit/delete on this file.
        return (
            f"Declined by user: {action} on {path} was not approved. The file was not modified. "
            "Do not retry this exact operation on this file — continue with other work, "
            "or ask the user before trying again."
        )

    @tool
    def read_file(
        path: str,
        offset: int = 0,
        limit: int = _MAX_READ_CHARS,
        line_start: int | None = None,
        line_end: int | None = None,
    ) -> str:
        """Read a file's text contents in the workspace.

        Large files are capped at ~20,000 chars by default — pass ``offset``
        (char index to start from) and ``limit`` to page through bigger files.
        You may also pass 1-based ``line_start``/``line_end`` to read by line.
        """
        try:
            target = _resolve(workspace_root, path)
        except WorkspaceEscapeError as exc:
            return f"Error: {exc}"
        if not target.exists():
            return f"Error: {path} does not exist"
        if not target.is_file():
            return f"Error: {path} is not a file"
        try:
            text = target.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return f"Error: {path} is not a text file"

        if line_start is not None or line_end is not None:
            lines = text.splitlines()
            start = max((line_start or 1) - 1, 0)
            end = line_end if line_end is not None else len(lines)
            if start >= len(lines):
                return f"Error: {path} has only {len(lines)} lines"
            numbered = [
                f"{lineno}: {line}"
                for lineno, line in enumerate(lines[start:end], start=start + 1)
            ]
            return kg_warning() + "\n".join(numbered)

        chunk = text[offset : offset + limit]
        if offset + limit < len(text):
            chunk += f"\n... [truncated, {len(text) - offset - limit} more chars — call again with a higher offset]"
        return kg_warning() + chunk

    @tool
    def list_dir(path: str = ".", depth: int | None = None, max_depth: int | None = None) -> str:
        """List files and subdirectories under a workspace-relative path.

        Pass ``depth`` or ``max_depth`` for a recursive tree-style listing.
        """
        requested_depth = depth if depth is not None else max_depth
        if requested_depth and requested_depth > 1:
            return project_tree.func(path, requested_depth)

        try:
            target = _resolve(workspace_root, path)
        except WorkspaceEscapeError as exc:
            return f"Error: {exc}"
        if not target.exists():
            return f"Error: {path} does not exist"
        entries = sorted(e for e in target.iterdir() if e.name not in _IGNORE_DIRS)
        if not entries:
            return kg_warning() + "(empty directory)"
        lines = []
        for entry in entries:
            marker = "/" if entry.is_dir() else ""
            lines.append(f"{entry.name}{marker}")
        return kg_warning() + "\n".join(lines)

    @tool
    def project_tree(path: str = ".", max_depth: int = 3) -> str:
        """Show a recursive directory tree (skipping .git/node_modules/venv/etc.),
        so you can quickly orient yourself in an unfamiliar project without many
        list_dir calls.
        """
        try:
            target = _resolve(workspace_root, path)
        except WorkspaceEscapeError as exc:
            return f"Error: {exc}"
        if not target.exists():
            return f"Error: {path} does not exist"

        lines: list[str] = []

        def walk(directory: Path, prefix: str, depth: int) -> None:
            if len(lines) >= _MAX_TREE_ENTRIES or depth > max_depth:
                return
            try:
                entries = sorted(
                    (e for e in directory.iterdir() if e.name not in _IGNORE_DIRS),
                    key=lambda e: (e.is_file(), e.name),
                )
            except OSError:
                return
            for entry in entries:
                if len(lines) >= _MAX_TREE_ENTRIES:
                    lines.append("... (truncated)")
                    return
                marker = "/" if entry.is_dir() else ""
                lines.append(f"{prefix}{entry.name}{marker}")
                if entry.is_dir():
                    walk(entry, prefix + "  ", depth + 1)

        walk(target, "", 1)
        return kg_warning() + ("\n".join(lines) if lines else "(empty)")

    @tool
    def glob_files(pattern: str, path: str = ".") -> str:
        """Find files matching a glob pattern (e.g. "**/*.py", "src/**/*.tsx")
        under a workspace-relative path. Returns up to 200 matches.
        """
        try:
            target = _resolve(workspace_root, path)
        except WorkspaceEscapeError as exc:
            return f"Error: {exc}"
        if not target.exists():
            return f"Error: {path} does not exist"

        matches = [
            str(p.relative_to(workspace_root))
            for p in target.glob(pattern)
            if p.is_file() and not _is_ignored(p.relative_to(workspace_root))
        ]
        matches.sort()
        if not matches:
            return "No files matched"
        if len(matches) > 200:
            matches = matches[:200] + [f"... ({len(matches) - 200} more)"]
        return kg_warning() + "\n".join(matches)

    @tool
    def search_code(
        pattern: str | None = None,
        path: str = ".",
        query: str | None = None,
        max_results: int = 50,
    ) -> str:
        """Search file contents for a plain-text substring under a workspace-relative path.

        Returns matching "file:line: text" results. ``query`` is accepted as
        an alias for ``pattern``.
        """
        pattern = pattern or query
        if not pattern:
            return "Error: search_code requires a pattern or query"

        try:
            target = _resolve(workspace_root, path)
        except WorkspaceEscapeError as exc:
            return f"Error: {exc}"
        if not target.exists():
            return f"Error: {path} does not exist"

        matches: list[str] = []
        for file_path in target.rglob("*"):
            rel = file_path.relative_to(workspace_root)
            if not file_path.is_file() or _is_ignored(rel):
                continue
            try:
                text = file_path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for lineno, line in enumerate(text.splitlines(), start=1):
                if pattern in line:
                    matches.append(f"{rel}:{lineno}: {line.strip()}")
                    if len(matches) >= max_results:
                        return kg_warning() + "\n".join(matches)
        return kg_warning() + ("\n".join(matches) if matches else "No matches found")

    @tool
    def write_file(path: str, content: str) -> str:
        """Create or overwrite a file in the workspace with the given content.

        Asks the user for confirmation before writing.
        """
        try:
            target = _resolve(workspace_root, path)
        except WorkspaceEscapeError as exc:
            return f"Error: {exc}"

        action = "overwrite" if target.exists() else "create"
        if not confirm(f"{action} file", str(target.relative_to(workspace_root))):
            return permission_declined(action, path)

        target.parent.mkdir(parents=True, exist_ok=True)
        result = _fix_and_retry(
            "write",
            target,
            lambda: (
                target.write_text(content, encoding="utf-8")
                or f"Wrote {len(content)} chars to {path}"
            ),
        )
        return result

    @tool
    def edit_file(path: str, old_text: str, new_text: str) -> str:
        """Replace the first exact occurrence of old_text with new_text in a workspace file.

        Asks the user for confirmation before editing. old_text must match
        exactly (including whitespace) and must be unique enough to identify
        the right spot — include a line or two of surrounding context if needed.
        """
        try:
            target = _resolve(workspace_root, path)
        except WorkspaceEscapeError as exc:
            return f"Error: {exc}"
        if not target.exists():
            return f"Error: {path} does not exist"

        context.edit_attempts[path] = context.edit_attempts.get(path, 0) + 1
        if context.edit_attempts[path] > _MAX_EDIT_ATTEMPTS_PER_FILE:
            return (
                f"HARD STOP: edit_file was called {context.edit_attempts[path]} times for {path} "
                "in this tool session. Do not call edit_file again for this file. "
                "Summarize the current state and ask for human review if more edits are needed."
            )

        original = target.read_text(encoding="utf-8")
        occurrences = original.count(old_text)
        if occurrences == 0:
            context.edit_failures[path] = context.edit_failures.get(path, 0) + 1
            if context.edit_failures[path] >= _MAX_EDIT_FAILURES_PER_FILE:
                return (
                    f"HARD STOP: edit_file failed {context.edit_failures[path]} times for {path}. "
                    "Do not call edit_file again for this file until you call read_file with a "
                    "narrow line_start/line_end range and quote the exact current text. "
                    "Summarize the blocker if you cannot get an exact match."
                )
            return (
                f"Error: old_text not found in {path}. Call read_file for the exact target "
                "line range before retrying edit_file; do not guess old_text."
            )
        if occurrences > 1:
            context.edit_failures[path] = context.edit_failures.get(path, 0) + 1
            if context.edit_failures[path] >= _MAX_EDIT_FAILURES_PER_FILE:
                return (
                    f"HARD STOP: edit_file matched multiple locations {context.edit_failures[path]} "
                    f"times for {path}. Do not call edit_file again until you call read_file "
                    "for a narrower line range and include unique surrounding context."
                )
            return (
                f"Error: old_text matches {occurrences} locations in {path} — "
                "call read_file for a narrower line range and include more surrounding context "
                "so the edit is unambiguous"
            )

        if not confirm("edit file", str(target.relative_to(workspace_root))):
            return permission_declined("edit", path)

        def _do_edit():
            target.write_text(original.replace(old_text, new_text, 1), encoding="utf-8")
            return f"Edited {path}"

        result = _fix_and_retry("edit", target, _do_edit)
        if result.startswith("Skipped") or result.startswith("Error"):
            # Don't clear edit_failures on a skip/error
            return result
        context.edit_failures.pop(path, None)
        return result

    @tool
    def delete_file(path: str) -> str:
        """Delete a file in the workspace. Asks the user for confirmation first."""
        try:
            target = _resolve(workspace_root, path)
        except WorkspaceEscapeError as exc:
            return f"Error: {exc}"
        if not target.exists():
            return f"Error: {path} does not exist"
        if not target.is_file():
            return f"Error: {path} is not a file"

        if not confirm("delete file", str(target.relative_to(workspace_root))):
            return permission_declined("delete", path)

        return _fix_and_retry(
            "delete",
            target,
            lambda: (target.unlink() or f"Deleted {path}"),
        )

    return [
        read_file,
        list_dir,
        project_tree,
        glob_files,
        search_code,
        write_file,
        edit_file,
        delete_file,
    ]
