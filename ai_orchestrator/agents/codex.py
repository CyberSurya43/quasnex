"""OpenAI Codex agent integration."""

from __future__ import annotations

from .base import AIAgent


class CodexAgent(AIAgent):
    """Codex agent with professional context."""
    
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key
    
    def send_message(self, prompt: str, context: list[dict[str, str]] | None = None) -> str:
        """Send message to Codex."""
        if not self.api_key:
            return "Error: CODEX_API_KEY not configured in .env file"
        
        # TODO: Implement actual Codex integration
        # This is a placeholder for the actual implementation
        # When implementing, use your Codex API client:
        # response = codex_client.complete(prompt, api_key=self.api_key)
        # return response.text
        
        return f"[Codex Ready] Configuration detected. Implement Codex API integration.\n\nQuery: {prompt[:100]}..."
