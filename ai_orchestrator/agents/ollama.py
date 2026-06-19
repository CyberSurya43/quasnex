"""Ollama local model agent integration.

Invokes the ``ollama`` CLI tool via subprocess for local model inference.
Falls back from the HTTP API approach to direct CLI invocation for
simplicity and consistency with the other CLI-based agents.
"""

from __future__ import annotations

from .base import AIAgent


class OllamaAgent(AIAgent):
    """Ollama local model agent using the ``ollama`` CLI.

    Runs ``ollama run <model> "<prompt>"`` as a subprocess.
    No network requests library needed — just the ``ollama`` binary.
    """

    cli_command = "ollama"

    def __init__(self, model: str = "qwen2.5-coder"):
        self.model = model

    def send_message(self, prompt: str, context: list[dict[str, str]] | None = None) -> str:
        """Send message to Ollama CLI and return the response."""
        available, detail = self.check_available()
        if not available:
            return (
                f"Error: {detail}. "
                "Install Ollama from https://ollama.com and run 'ollama serve'"
            )

        # Build context-aware prompt
        full_prompt = self._build_prompt(prompt, context)

        command = ["ollama", "run", self.model, full_prompt]

        returncode, stdout, stderr = self._run_cli(command, timeout=120)

        if returncode == 0 and stdout:
            is_valid, reason = self.validate_response(stdout)
            if is_valid:
                return stdout
            else:
                return f"Error: Invalid response from Ollama — {reason}"

        # Handle common failure modes
        if "not found" in (stderr or "").lower():
            return (
                f"Error: Model '{self.model}' not found. "
                f"Pull it first with: ollama pull {self.model}"
            )

        if "connection refused" in (stderr or "").lower():
            return (
                "Error: Cannot connect to Ollama. "
                "Make sure Ollama is running with 'ollama serve'"
            )

        error_detail = stderr or stdout or "No output"
        return f"Error: Ollama CLI failed (exit {returncode}): {error_detail}"

    def _build_prompt(self, prompt: str, context: list[dict[str, str]] | None) -> str:
        """Build prompt with conversation context."""
        if not context:
            return prompt

        # Add recent context (last 5 messages)
        recent_context = context[-5:] if len(context) > 5 else context

        prompt_parts = ["Previous conversation:"]
        for msg in recent_context:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            prompt_parts.append(f"{role}: {content[:200]}...")  # Truncate long messages

        prompt_parts.append("\nCurrent query:")
        prompt_parts.append(prompt)

        return "\n".join(prompt_parts)
