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
    "openai/gpt-oss-120b",
    "qwen/qwen3-next-80b-a3b-instruct",
    "qwen/qwen2.5-coder-32b-instruct",
    "openai/gpt-oss-20b",
    "meta/llama-3.1-70b-instruct",
    "mistralai/mistral-nemotron",
    "deepseek-ai/deepseek-v4-flash",
)
_DEFAULT_TEMPERATURE = 0.2
_DEFAULT_MAX_RETRIES = 2
_MODEL_ROLES = (
    "planner",
    "repository_search",
    "documentation",
    "coding",
    "debugging",
    "testing",
    "deployment",
)


@dataclass(frozen=True)
class ProviderConfig:
    """A single OpenAI-compatible model provider (Lightning gateway, NVIDIA NIM, ...)."""
    name: str
    base_url: str
    api_key: str
    models: tuple[str, ...]
    temperature: float = _DEFAULT_TEMPERATURE
    max_retries: int = _DEFAULT_MAX_RETRIES


@dataclass(frozen=True)
class ModelRoute:
    """A concrete model selected for a task capability."""
    provider: str
    model: str

    @property
    def label(self) -> str:
        return f"{self.provider}:{self.model}"


@dataclass
class EnvironmentConfig:
    """Configuration loaded from .env file for model access."""
    default_provider: str = "lightning"
    providers: dict[str, ProviderConfig] = field(default_factory=dict)
    role_models: dict[str, tuple[ModelRoute, ...]] = field(default_factory=dict)


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


def _parse_model_route(raw: str, role: str, providers: dict[str, ProviderConfig]) -> ModelRoute:
    if ":" not in raw:
        raise ValueError(
            f"{role.upper()}_MODEL must use '<provider>:<model>', got {raw!r}"
        )
    provider_name, _, model_name = raw.partition(":")
    provider_name = provider_name.strip()
    model_name = model_name.strip()
    if provider_name not in providers:
        raise ValueError(
            f"{role.upper()}_MODEL references unknown provider {provider_name!r}. "
            f"Available: {', '.join(providers)}"
        )
    if model_name not in providers[provider_name].models:
        raise ValueError(
            f"{role.upper()}_MODEL references model {model_name!r}, which is not "
            f"configured for provider {provider_name!r}. Available: "
            f"{', '.join(providers[provider_name].models)}"
        )
    return ModelRoute(provider_name, model_name)


def _route_if_available(
    provider_name: str,
    model_name: str,
    providers: dict[str, ProviderConfig],
) -> ModelRoute | None:
    provider = providers.get(provider_name)
    if provider is None or model_name not in provider.models:
        return None
    return ModelRoute(provider_name, model_name)


def _first_configured_coder(providers: dict[str, ProviderConfig]) -> ModelRoute | None:
    provider = providers.get("nvidia")
    if provider is None:
        return None
    for model_name in provider.models:
        lowered = model_name.lower()
        if "coder" in lowered or "codestral" in lowered or "deepseek-coder" in lowered:
            return ModelRoute("nvidia", model_name)
    return None


def _dedupe_routes(routes: list[ModelRoute]) -> tuple[ModelRoute, ...]:
    seen: set[tuple[str, str]] = set()
    deduped: list[ModelRoute] = []
    for route in routes:
        key = (route.provider, route.model)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(route)
    return tuple(deduped)


def _default_role_routes(providers: dict[str, ProviderConfig]) -> dict[str, tuple[ModelRoute, ...]]:
    def available(*candidates: tuple[str, str]) -> list[ModelRoute]:
        routes: list[ModelRoute] = []
        for provider_name, model_name in candidates:
            route = _route_if_available(provider_name, model_name, providers)
            if route is not None:
                routes.append(route)
        return routes

    nvidia_coder = _first_configured_coder(providers)
    role_routes: dict[str, list[ModelRoute]] = {
        "planner": available(
            ("nvidia", "openai/gpt-oss-120b"),
            ("nvidia", "qwen/qwen3-next-80b-a3b-instruct"),
            ("lightning", "qwen2.5-coder:14b"),
        ),
        "repository_search": available(
            ("nvidia", "qwen/qwen3-next-80b-a3b-instruct"),
            ("nvidia", "openai/gpt-oss-120b"),
        ),
        "documentation": available(
            ("nvidia", "qwen/qwen3-next-80b-a3b-instruct"),
            ("nvidia", "openai/gpt-oss-120b"),
        ),
        # "coding"/"debugging" are built below the dict: the strongest
        # code-tuned OSS model configured (e.g. qwen2.5-coder-32b-instruct)
        # leads, then the largest general OSS model, with the small local
        # model as a last-resort fallback for lightning-only setups.
        "coding": [],
        "debugging": [],
        "testing": available(
            ("nvidia", "openai/gpt-oss-120b"),
            ("lightning", "qwen2.5-coder:14b"),
        ),
        "deployment": available(
            ("nvidia", "openai/gpt-oss-120b"),
            ("nvidia", "qwen/qwen3-next-80b-a3b-instruct"),
        ),
    }
    for role in ("coding", "debugging"):
        if nvidia_coder is not None:
            role_routes[role].append(nvidia_coder)
        role_routes[role].extend(available(("nvidia", "openai/gpt-oss-120b")))
        role_routes[role].extend(available(("lightning", "qwen2.5-coder:14b")))

    if providers:
        first_provider_name = next(iter(providers))
        fallback = ModelRoute(first_provider_name, providers[first_provider_name].models[0])
        for role in _MODEL_ROLES:
            role_routes.setdefault(role, []).append(fallback)

    return {role: _dedupe_routes(routes) for role, routes in role_routes.items()}


def _load_role_routes(
    env_vars: dict[str, str],
    providers: dict[str, ProviderConfig],
) -> dict[str, tuple[ModelRoute, ...]]:
    role_routes = _default_role_routes(providers)
    for role in _MODEL_ROLES:
        override = _get(env_vars, f"{role.upper()}_MODEL")
        if override:
            route = _parse_model_route(override, role, providers)
            existing = [r for r in role_routes.get(role, ()) if r != route]
            role_routes[role] = (route, *existing)
    return role_routes


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

    role_models = _load_role_routes(env_vars, providers)

    return EnvironmentConfig(
        default_provider=default_provider,
        providers=providers,
        role_models=role_models,
    )


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
    every stage, just with a different system-prompt persona. A provider value
    only affects final fallback ordering after capability-role candidates fail.
    """
    name: str
    role: str
    provider: str | None = None    # fallback provider key, e.g. "lightning"; None = configured order


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
