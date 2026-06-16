from __future__ import annotations

import json
import subprocess
from abc import ABC, abstractmethod
from typing import Any


class AIAgent(ABC):
    """Base class for AI agent integrations."""
    
    @abstractmethod
    def send_message(self, prompt: str, context: list[dict[str, str]] | None = None) -> str:
        """Send a message and get response."""
        pass


class OllamaAgent(AIAgent):
    """Ollama local model agent."""
    
    def __init__(self, model: str = "qwen2.5-coder", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url
    
    def send_message(self, prompt: str, context: list[dict[str, str]] | None = None) -> str:
        """Send message to Ollama."""
        try:
            result = subprocess.run(
                ["ollama", "run", self.model, prompt],
                capture_output=True,
                text=True,
                check=False,
            )
            
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return f"Error: {result.stderr.strip()}"
        except FileNotFoundError:
            return "Error: Ollama CLI not found. Install from https://ollama.ai"


class GeminiAgent(AIAgent):
    """Google Gemini agent."""
    
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key
    
    def send_message(self, prompt: str, context: list[dict[str, str]] | None = None) -> str:
        """Send message to Gemini API."""
        if not self.api_key:
            return "Error: GEMINI_API_KEY not configured in .env file"
        
        # Placeholder - actual Gemini API integration
        return f"[Gemini] Would send: {prompt}"


class CodexAgent(AIAgent):
    """Codex agent."""
    
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key
    
    def send_message(self, prompt: str, context: list[dict[str, str]] | None = None) -> str:
        """Send message to Codex."""
        if not self.api_key:
            return "Error: CODEX_API_KEY not configured in .env file"
        
        # Placeholder - actual Codex integration
        return f"[Codex] Would send: {prompt}"


def create_agent(agent_type: str, api_key: str | None = None, model: str | None = None) -> AIAgent:
    """Factory function to create AI agents."""
    if agent_type == "ollama":
        return OllamaAgent(model or "qwen2.5-coder")
    elif agent_type == "gemini":
        return GeminiAgent(api_key)
    elif agent_type == "codex":
        return CodexAgent(api_key)
    else:
        raise ValueError(f"Unknown agent type: {agent_type}")
