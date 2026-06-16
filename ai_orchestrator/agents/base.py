"""Base class for AI agent integrations."""

from __future__ import annotations

from abc import ABC, abstractmethod


class AIAgent(ABC):
    """Base class for AI agent integrations."""
    
    @abstractmethod
    def send_message(self, prompt: str, context: list[dict[str, str]] | None = None) -> str:
        """Send a message and get response."""
        pass
    
    def validate_response(self, response: str) -> tuple[bool, str]:
        """Validate agent response quality."""
        if not response or len(response.strip()) < 10:
            return False, "Response too short or empty"
        
        error_indicators = ["error:", "failed", "cannot", "unable", "not available"]
        if any(indicator in response.lower()[:100] for indicator in error_indicators):
            return False, "Response contains error indicators"
        
        return True, "Valid response"
