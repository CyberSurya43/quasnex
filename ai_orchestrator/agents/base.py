"""Base class for AI agent integrations."""

from __future__ import annotations

import shutil
import subprocess
from abc import ABC, abstractmethod


class AIAgent(ABC):
    """Base class for AI agent integrations.

    All agents invoke external CLI tools (codex, claude, ollama) via subprocess
    rather than calling cloud APIs directly with API keys.
    """

    # Subclasses should set this to the CLI command name (e.g. "codex", "claude", "ollama")
    cli_command: str = ""

    @abstractmethod
    def send_message(self, prompt: str, context: list[dict[str, str]] | None = None) -> str:
        """Send a message and get response."""
        pass

    @classmethod
    def check_available(cls) -> tuple[bool, str]:
        """Check whether the required CLI tool is installed and reachable.

        Returns:
            (is_available, detail_message)
        """
        if not cls.cli_command:
            return False, f"{cls.__name__} does not define a cli_command"

        path = shutil.which(cls.cli_command)
        if path:
            return True, f"{cls.cli_command} found at {path}"
        return False, f"{cls.cli_command} not found in PATH"

    @staticmethod
    def _run_cli(
        command: list[str],
        *,
        timeout: int = 300,
        cwd: str | None = None,
        stdin_data: str | None = None,
    ) -> tuple[int, str, str]:
        """Run a CLI command via subprocess and return (returncode, stdout, stderr).

        Args:
            command: Command and arguments as a list.
            timeout: Maximum seconds to wait (default 5 minutes).
            cwd: Working directory for the command.
            stdin_data: Optional string to feed to the process via stdin.

        Returns:
            Tuple of (return_code, stdout_text, stderr_text).
        """
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
                # Always close stdin so CLI tools don't hang in interactive mode.
                # Pass the caller's data if provided, otherwise send empty string
                # which opens a PIPE and immediately sends EOF.
                input=stdin_data if stdin_data is not None else "",
            )
            return result.returncode, result.stdout.strip(), result.stderr.strip()

        except subprocess.TimeoutExpired:
            return -1, "", f"Command timed out after {timeout}s: {' '.join(command)}"

        except FileNotFoundError:
            return -1, "", f"Command not found: {command[0]}"

        except Exception as exc:
            return -1, "", f"Unexpected error running {command[0]}: {exc}"

    def validate_response(self, response: str) -> tuple[bool, str]:
        """Validate agent response quality.

        With CLI-based agents, error detection relies primarily on exit codes
        and stderr. This validation catches obviously broken responses only.
        """
        if not response or len(response.strip()) < 1:
            return False, "Response is empty"

        error_indicators = ["error:", "failed", "cannot", "unable", "not available"]
        if any(indicator in response.lower()[:100] for indicator in error_indicators):
            return False, "Response contains error indicators"

        return True, "Valid response"
