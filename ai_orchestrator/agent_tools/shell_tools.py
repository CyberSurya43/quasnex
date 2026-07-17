"""Shell execution tools, for running tests/builds/git/deploy commands.

``run_shell`` and ``run_tests`` execute arbitrary/detected commands and are
gated behind confirmation. ``git_status``/``git_diff`` are read-only and run
unconfirmed so the agent can freely check its own progress.
"""

from __future__ import annotations

import shlex
import subprocess
from pathlib import Path

from langchain_core.tools import BaseTool, tool

from .confirm import confirm

_DEFAULT_TIMEOUT = 300
_OUTPUT_CAP = 4000


def _run(command: list[str], workspace_root: Path, timeout: int = _DEFAULT_TIMEOUT) -> str:
    try:
        result = subprocess.run(
            command,
            cwd=workspace_root,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return f"Error: command timed out after {timeout}s"
    except FileNotFoundError as exc:
        return f"Error: {exc}"

    output = (result.stdout or "") + (result.stderr or "")
    return f"exit code: {result.returncode}\n{output[:_OUTPUT_CAP]}"


def _detect_test_command(workspace_root: Path) -> str | None:
    if (workspace_root / "pytest.ini").exists() or (workspace_root / "pyproject.toml").exists():
        return "python -m pytest -q"
    if (workspace_root / "manage.py").exists():
        return "python manage.py test"
    if (workspace_root / "package.json").exists():
        return "npm test --silent"
    if (workspace_root / "go.mod").exists():
        return "go test ./..."
    if (workspace_root / "Cargo.toml").exists():
        return "cargo test"
    return None


def build_tools(workspace_root: Path) -> list[BaseTool]:
    workspace_root = workspace_root.resolve()

    @tool
    def run_shell(command: str) -> str:
        """Run a shell command inside the project workspace (builds, git, docker, one-offs).

        Asks the user for confirmation before executing. Output is truncated to 4000 chars.
        Prefer run_tests for running the test suite.
        """
        if not confirm("run shell command", command):
            return f"Declined by user: not running `{command}`"
        return _run(shlex.split(command), workspace_root)

    @tool
    def run_tests(command: str | None = None) -> str:
        """Run the project's test suite.

        Auto-detects pytest/Django/npm/go/cargo from the workspace if no
        explicit command is given. Asks the user for confirmation before running.
        """
        cmd = command or _detect_test_command(workspace_root)
        if cmd is None:
            return (
                "Error: could not auto-detect a test command for this project. "
                "Pass an explicit `command`, e.g. run_tests(command='pytest tests/unit')."
            )
        if not confirm("run tests", cmd):
            return f"Declined by user: not running `{cmd}`"
        return _run(shlex.split(cmd), workspace_root, timeout=600)

    @tool
    def git_status() -> str:
        """Show `git status` for the workspace (read-only, no confirmation needed)."""
        return _run(["git", "status", "--short", "--branch"], workspace_root, timeout=30)

    @tool
    def git_diff(path: str = "") -> str:
        """Show `git diff` for the workspace, optionally scoped to one path (read-only)."""
        command = ["git", "diff"] + ([path] if path else [])
        return _run(command, workspace_root, timeout=30)

    return [run_shell, run_tests, git_status, git_diff]
