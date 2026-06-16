from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class EnvironmentConfig:
    """Configuration loaded from .env file for API keys and Ollama settings."""
    gemini_api_key: str | None = None
    codex_api_key: str | None = None
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5-coder"


def load_env(project_dir: Path) -> EnvironmentConfig:
    """Load environment configuration from .env file in project directory."""
    env_path = project_dir / ".env"
    
    if not env_path.exists():
        return EnvironmentConfig()
    
    env_vars: dict[str, str] = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            env_vars[key.strip()] = value.strip()
    
    return EnvironmentConfig(
        gemini_api_key=env_vars.get("GEMINI_API_KEY"),
        codex_api_key=env_vars.get("CODEX_API_KEY"),
        ollama_base_url=env_vars.get("OLLAMA_BASE_URL", "http://localhost:11434"),
        ollama_model=env_vars.get("OLLAMA_MODEL", "qwen2.5-coder"),
    )


def get_env_var(name: str, default: str | None = None) -> str | None:
    """Get an environment variable from the process environment."""
    return os.getenv(name, default)
