"""Filesystem tools for the coding agent, scoped to a workspace root.

Reads are unrestricted. Writes/edits require confirmation (see ``confirm.py``)
and are always resolved relative to, and confined within, the workspace root
so the agent can't wander outside the project directory.
"""

from __future__ import annotations

from pathlib import Path

from langchain_core.tools import BaseTool, tool

from .confirm import confirm

_IGNORE_DIRS = {
    ".git", ".orchestrator", ".venv", "venv", "node_modules", "__pycache__",
    ".pytest_cache", ".mypy_cache", "dist", "build", ".next", ".cache", "egg-info",
}
_MAX_READ_CHARS = 20_000
_MAX_TREE_ENTRIES = 400


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


def build_tools(workspace_root: Path) -> list[BaseTool]:
    workspace_root = workspace_root.resolve()
    workspace_root.mkdir(parents=True, exist_ok=True)

    @tool
    def read_file(path: str, offset: int = 0, limit: int = _MAX_READ_CHARS) -> str:
        """Read a file's text contents in the workspace.

        Large files are capped at ~20,000 chars by default — pass ``offset``
        (char index to start from) and ``limit`` to page through bigger files.
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

        chunk = text[offset : offset + limit]
        if offset + limit < len(text):
            chunk += f"\n... [truncated, {len(text) - offset - limit} more chars — call again with a higher offset]"
        return chunk

    @tool
    def list_dir(path: str = ".") -> str:
        """List files and subdirectories under a workspace-relative path."""
        try:
            target = _resolve(workspace_root, path)
        except WorkspaceEscapeError as exc:
            return f"Error: {exc}"
        if not target.exists():
            return f"Error: {path} does not exist"
        entries = sorted(e for e in target.iterdir() if e.name not in _IGNORE_DIRS)
        if not entries:
            return "(empty directory)"
        lines = []
        for entry in entries:
            marker = "/" if entry.is_dir() else ""
            lines.append(f"{entry.name}{marker}")
        return "\n".join(lines)

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
        return "\n".join(lines) if lines else "(empty)"

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
        return "\n".join(matches)

    @tool
    def search_code(pattern: str, path: str = ".") -> str:
        """Search file contents for a plain-text substring under a workspace-relative path.

        Returns up to 50 matching "file:line: text" results.
        """
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
                    if len(matches) >= 50:
                        return "\n".join(matches)
        return "\n".join(matches) if matches else "No matches found"

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
            return f"Declined by user: not writing {path}"

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"Wrote {len(content)} chars to {path}"

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

        original = target.read_text(encoding="utf-8")
        occurrences = original.count(old_text)
        if occurrences == 0:
            return f"Error: old_text not found in {path}"
        if occurrences > 1:
            return (
                f"Error: old_text matches {occurrences} locations in {path} — "
                "include more surrounding context so the edit is unambiguous"
            )

        if not confirm("edit file", str(target.relative_to(workspace_root))):
            return f"Declined by user: not editing {path}"

        target.write_text(original.replace(old_text, new_text, 1), encoding="utf-8")
        return f"Edited {path}"

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
            return f"Declined by user: not deleting {path}"

        target.unlink()
        return f"Deleted {path}"

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
