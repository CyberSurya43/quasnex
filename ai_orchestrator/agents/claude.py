"""Claude Code CLI agent integration.

Invokes the ``claude`` CLI tool via subprocess for frontend, UI/UX, and
design tasks. No API key management required — Claude Code CLI handles
its own authentication.
"""

from __future__ import annotations

import json as _json

from .base import AIAgent


class ClaudeAgent(AIAgent):
    """Claude Code agent that delegates work to the ``claude`` CLI.

    Claude Code is Anthropic's terminal-native coding agent.
    We invoke it in non-interactive (print) mode using ``claude -p "<prompt>"``.
    """

    cli_command = "claude"

    def __init__(self, model: str | None = None):
        self.model = model  # e.g. "claude-sonnet-4"; None = use CLI default

    def send_message(self, prompt: str, context: list[dict[str, str]] | None = None) -> str:
        """Send prompt to Claude Code CLI and return the response."""
        available, detail = self.check_available()
        if not available:
            return f"Error: {detail}. Install Claude Code from https://claude.ai/install.sh"

        # Build context-aware prompt
        full_prompt = self._build_prompt(prompt, context)

        command = [
            "claude",
            "-p", full_prompt,
            "--output-format", "json",
        ]

        if self.model:
            command.extend(["--model", self.model])

        returncode, stdout, stderr = self._run_cli(command, timeout=300)

        if returncode == 0 and stdout:
            # Try to parse structured JSON output
            response_text = self._extract_response(stdout)
            if response_text:
                is_valid, reason = self.validate_response(response_text)
                if is_valid:
                    return response_text
                else:
                    return f"Error: Invalid response from Claude — {reason}"

        # Build a meaningful error message
        error_detail = stderr or stdout or "No output"
        return f"Error: Claude CLI failed (exit {returncode}): {error_detail}"

    def _extract_response(self, raw_output: str) -> str:
        """Extract the response text from Claude CLI output.

        Claude's ``--output-format json`` returns a JSON object with a
        ``result`` field containing the response text. If JSON parsing
        fails, fall back to using the raw output as plain text.
        """
        try:
            data = _json.loads(raw_output)
            # Claude JSON output has a 'result' field
            if isinstance(data, dict):
                return data.get("result", raw_output)
            return raw_output
        except (_json.JSONDecodeError, TypeError):
            # Not JSON — treat as plain text response
            return raw_output

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
