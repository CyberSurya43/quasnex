"""Configuration management and environment loading."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
import tomllib


# -----------------------------------------------------------------------
# Environment Configuration
# -----------------------------------------------------------------------

_DEFAULT_NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
_DEFAULT_NVIDIA_MODELS = (
    "qwen/qwen3-next-80b-a3b-instruct",
    "openai/gpt-oss-20b",
    "mistralai/codestral-22b-instruct-v0.1",
    "deepseek-ai/deepseek-coder-6.7b-instruct",
)
_DEFAULT_TEMPERATURE = 0.2
_DEFAULT_MAX_RETRIES = 2


@dataclass(frozen=True)
class ProviderConfig:
    """A single OpenAI-compatible model provider (Lightning gateway, NVIDIA NIM, ...)."""
    name: str
    base_url: str
    api_key: str
    models: tuple[str, ...]
    temperature: float = _DEFAULT_TEMPERATURE
    max_retries: int = _DEFAULT_MAX_RETRIES


@dataclass
class EnvironmentConfig:
    """Configuration loaded from .env file for model access."""
    default_provider: str = "lightning"
    providers: dict[str, ProviderConfig] = field(default_factory=dict)


def _read_env_file(project_dir: Path) -> dict[str, str]:
    env_vars: dict[str, str] = {}
    env_path = project_dir / ".env"
    if not env_path.exists():
        return env_vars
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            env_vars[key.strip()] = value.strip()
    return env_vars


def _get(env_vars: dict[str, str], name: str, default: str | None = None) -> str | None:
    """Env file value wins, falling back to the process environment, then default."""
    return env_vars.get(name) or os.getenv(name) or default


def _get_float(env_vars: dict[str, str], name: str, default: float) -> float:
    raw = _get(env_vars, name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _get_int(env_vars: dict[str, str], name: str, default: int) -> int:
    raw = _get(env_vars, name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def load_env(project_dir: Path) -> EnvironmentConfig:
    """Load model-provider configuration from a .env file in project_dir (or cwd)."""
    env_vars = _read_env_file(project_dir)

    providers: dict[str, ProviderConfig] = {}

    # Global fallback, overridable per-provider (e.g. LIGHTNING_TEMPERATURE wins
    # over DEFAULT_TEMPERATURE for the lightning provider specifically).
    default_temperature = _get_float(env_vars, "DEFAULT_TEMPERATURE", _DEFAULT_TEMPERATURE)
    default_max_retries = _get_int(env_vars, "DEFAULT_MAX_RETRIES", _DEFAULT_MAX_RETRIES)

    lightning_key = _get(env_vars, "LIGHTNING_API_KEY")
    lightning_url = _get(env_vars, "LIGHTNING_BASE_URL")
    if lightning_url and lightning_key:
        models = tuple(
            m.strip() for m in _get(env_vars, "LIGHTNING_MODELS", "").split(",") if m.strip()
        )
        providers["lightning"] = ProviderConfig(
            name="lightning",
            base_url=lightning_url,
            api_key=lightning_key,
            models=models or ("qwen2.5-coder:14b",),
            temperature=_get_float(env_vars, "LIGHTNING_TEMPERATURE", default_temperature),
            max_retries=_get_int(env_vars, "LIGHTNING_MAX_RETRIES", default_max_retries),
        )

    nvidia_key = _get(env_vars, "NVIDIA_API_KEY")
    if nvidia_key:
        models = tuple(
            m.strip() for m in _get(env_vars, "NVIDIA_MODELS", "").split(",") if m.strip()
        )
        providers["nvidia"] = ProviderConfig(
            name="nvidia",
            base_url=_get(env_vars, "NVIDIA_BASE_URL", _DEFAULT_NVIDIA_BASE_URL),
            api_key=nvidia_key,
            models=models or _DEFAULT_NVIDIA_MODELS,
            temperature=_get_float(env_vars, "NVIDIA_TEMPERATURE", default_temperature),
            max_retries=_get_int(env_vars, "NVIDIA_MAX_RETRIES", default_max_retries),
        )

    default_provider = _get(env_vars, "DEFAULT_PROVIDER", next(iter(providers), "lightning"))

    return EnvironmentConfig(default_provider=default_provider, providers=providers)


def load_providers(project_dir: Path) -> dict[str, ProviderConfig]:
    """Convenience accessor: just the configured providers."""
    return load_env(project_dir).providers


def get_env_var(name: str, default: str | None = None) -> str | None:
    """Get an environment variable from the process environment."""
    return os.getenv(name, default)


# -----------------------------------------------------------------------
# Project Configuration
# -----------------------------------------------------------------------

@dataclass(frozen=True)
class AgentConfig:
    """A persona the LangGraph agent adopts for a stage.

    No shell command templates anymore — the same tool-using agent executes
    every stage, just with a different system-prompt persona and (optionally)
    a preferred model provider.
    """
    name: str
    role: str
    provider: str | None = None    # preferred provider key, e.g. "lightning"; None = use active


@dataclass(frozen=True)
class StageConfig:
    name: str
    agent: str
    title: str
    objective: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    acceptance: tuple[str, ...]


@dataclass(frozen=True)
class ProjectConfig:
    name: str
    workspace: Path
    stack: dict[str, str]
    agents: dict[str, AgentConfig]
    stages: tuple[StageConfig, ...]


def load_config(project_dir: Path) -> ProjectConfig:
    config_path = project_dir / "orchestrator.toml"
    if not config_path.exists():
        raise FileNotFoundError(f"Missing orchestrator config: {config_path}")

    data = tomllib.loads(config_path.read_text(encoding="utf-8"))
    project = data.get("project", {})
    agents_data = data.get("agents", {})
    stages_data = data.get("stages", [])

    if not project.get("name"):
        raise ValueError("orchestrator.toml must define [project].name")
    if not stages_data:
        raise ValueError("orchestrator.toml must define at least one [[stages]] entry")

    agents: dict[str, AgentConfig] = {}
    for key, value in agents_data.items():
        agents[key] = AgentConfig(
            name=value.get("name", key),
            role=value.get("role", ""),
            provider=value.get("provider") or None,
        )

    if not agents:
        raise ValueError("orchestrator.toml must define at least one [agents.<id>] entry")

    stages: list[StageConfig] = []
    for raw_stage in stages_data:
        stage = StageConfig(
            name=_required(raw_stage, "name"),
            agent=_required(raw_stage, "agent"),
            title=_required(raw_stage, "title"),
            objective=_required(raw_stage, "objective"),
            inputs=tuple(raw_stage.get("inputs", [])),
            outputs=tuple(raw_stage.get("outputs", [])),
            acceptance=tuple(raw_stage.get("acceptance", [])),
        )
        if stage.agent not in agents:
            raise ValueError(f"Stage {stage.name!r} references unknown agent {stage.agent!r}")
        stages.append(stage)

    workspace = project_dir / project.get("workspace", "workspace")
    return ProjectConfig(
        name=project["name"],
        workspace=workspace,
        stack=dict(data.get("stack", {})),
        agents=agents,
        stages=tuple(stages),
    )


def _required(data: dict[str, object], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Stage entry must define {key!r}")
    return value
