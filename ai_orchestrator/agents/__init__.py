"""AI agent integrations.

All agents invoke external CLI tools via subprocess rather than calling
cloud APIs directly with API keys.
"""

from .base import AIAgent
from .ollama import OllamaAgent
from .claude import ClaudeAgent
from .codex import CodexAgent


def create_agent(
    agent_type: str,
    *,
    model: str | None = None,
    approval_mode: str = "full-auto",
) -> AIAgent:
    """Factory function to create AI agents.

    Args:
        agent_type: One of "ollama", "claude", "codex".
        model: Model name (used by ollama and claude).
        approval_mode: Codex approval mode (default "full-auto").
    """
    if agent_type == "ollama":
        return OllamaAgent(model or "qwen2.5-coder")
    elif agent_type == "claude":
        return ClaudeAgent(model)
    elif agent_type == "codex":
        return CodexAgent(approval_mode)
    else:
        raise ValueError(f"Unknown agent type: {agent_type}")


__all__ = ["AIAgent", "OllamaAgent", "ClaudeAgent", "CodexAgent", "create_agent"]
