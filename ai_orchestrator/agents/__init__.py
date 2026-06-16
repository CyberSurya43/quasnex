"""AI agent integrations."""

from .base import AIAgent
from .ollama import OllamaAgent
from .gemini import GeminiAgent
from .codex import CodexAgent


def create_agent(agent_type: str, api_key: str | None = None, model: str | None = None) -> AIAgent:
    """Factory function to create AI agents with professional context."""
    if agent_type == "ollama":
        return OllamaAgent(model or "qwen2.5-coder")
    elif agent_type == "gemini":
        return GeminiAgent(api_key)
    elif agent_type == "codex":
        return CodexAgent(api_key)
    else:
        raise ValueError(f"Unknown agent type: {agent_type}")


__all__ = ["AIAgent", "OllamaAgent", "GeminiAgent", "CodexAgent", "create_agent"]
