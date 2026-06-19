"""OpenAI Codex CLI agent integration.

Invokes the `codex` CLI tool via subprocess for backend, orchestration,
testing, and deployment tasks. No API key management required — Codex CLI
handles its own authentication.
"""

from __future__ import annotations

from .base import AIAgent


class CodexAgent(AIAgent):
    """Codex agent that delegates work to the Codex CLI.

    The Codex CLI is a terminal-native coding agent by OpenAI.
    We invoke it in non-interactive mode using ``codex -p "<prompt>"``.
    """

    cli_command = "codex"

    def __init__(self, approval_mode: str = "full-auto"):
        self.approval_mode = approval_mode

    def send_message(self, prompt: str, context: list[dict[str, str]] | None = None) -> str:
        """Send prompt to Codex CLI and return the response."""
        available, detail = self.check_available()
        if not available:
            return f"Error: {detail}. Install with: npm install -g @openai/codex"

        # Build context-aware prompt
        full_prompt = self._build_prompt(prompt, context)

        command = [
            "codex",
            "--approval-mode", self.approval_mode,
            "--quiet",
            "-p", full_prompt,
        ]

        returncode, stdout, stderr = self._run_cli(command, timeout=300)

        if returncode == 0 and stdout:
            is_valid, reason = self.validate_response(stdout)
            if is_valid:
                return stdout
            else:
                return f"Error: Invalid response from Codex — {reason}"

        # Build a meaningful error message
        error_detail = stderr or stdout or "No output"
        return f"Error: Codex CLI failed (exit {returncode}): {error_detail}"

    def _build_prompt(self, prompt: str, context: list[dict[str, str]] | None) -> str:
        """Build prompt with conversation context."""
        if not context:
            return prompt

        recent_context = context[-5:] if len(context) > 5 else context

        prompt_parts = ["Previous conversation:"]
        for msg in recent_context:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            prompt_parts.append(f"{role}: {content[:200]}")

        prompt_parts.append("\nCurrent query:")
        prompt_parts.append(prompt)

        return "\n".join(prompt_parts)
