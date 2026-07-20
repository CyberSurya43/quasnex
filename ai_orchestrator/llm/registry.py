"""Runtime-switchable model registry.

Holds the active (provider, model) pair for a project, persists the choice
through the existing shared-context store so it survives across chat
sessions, and builds fresh ``ChatOpenAI`` instances on demand — needed
because switching models mid-chat means rebinding the LangGraph agent to a
new LLM.
"""

from __future__ import annotations

from pathlib import Path

from langchain_openai import ChatOpenAI

from ..config import EnvironmentConfig, ModelRoute, ProviderConfig, load_env
from .providers import build_chat_model

# Imported lazily inside methods (not at module scope) to avoid a circular
# import: ai_orchestrator.core imports the LangGraph agent, which imports
# this registry.



class UnknownProviderError(ValueError):
    pass


class UnknownModelError(ValueError):
    pass


class UnknownModelRoleError(ValueError):
    pass


class ModelRegistry:
    """Tracks which provider/model is active and can (re)build the LLM."""

    def __init__(self, project_dir: Path | None = None):
        from ..core import context as ctx_store

        self.project_dir = project_dir or Path.cwd()
        self.env_config: EnvironmentConfig = load_env(self.project_dir)

        if not self.env_config.providers:
            raise RuntimeError(
                "No model providers configured. Set LIGHTNING_BASE_URL/LIGHTNING_API_KEY "
                "and/or NVIDIA_API_KEY in .env."
            )

        saved = ctx_store.load(self.project_dir).get("user_preferences", {}).get("model_settings", {})
        provider_name = saved.get("provider") or self.env_config.default_provider
        if provider_name not in self.env_config.providers:
            provider_name = next(iter(self.env_config.providers))
        model_name = saved.get("model") or self.env_config.providers[provider_name].models[0]

        self._provider_name = provider_name
        self._model_name = model_name

    # ------------------------------------------------------------------

    def current(self) -> tuple[str, str]:
        """Return (provider_name, model_name)."""
        return self._provider_name, self._model_name

    def list_available(self) -> dict[str, tuple[str, ...]]:
        """Return {provider_name: (model, ...)} for every configured provider."""
        return {name: cfg.models for name, cfg in self.env_config.providers.items()}

    def list_internal_available(self) -> dict[str, tuple[str, ...]]:
        """Return the full model inventory for routing and tests."""
        return self.list_available()

    def list_visible_models(self) -> dict[str, tuple[str, ...]]:
        """Return only the planner/orchestrator model for user-facing model lists."""
        route = self.planner_model()
        return {route.provider: (route.model,)}

    def other_providers(self) -> list[str]:
        """Configured providers other than the currently active one, for fallback."""
        return [name for name in self.env_config.providers if name != self._provider_name]

    def role_candidates(self, role: str) -> tuple[ModelRoute, ...]:
        """Return configured model candidates for a capability role."""
        try:
            candidates = self.env_config.role_models[role]
        except KeyError as exc:
            raise UnknownModelRoleError(
                f"Unknown model role {role!r}. Available: "
                f"{', '.join(sorted(self.env_config.role_models))}"
            ) from exc
        if not candidates:
            raise UnknownModelRoleError(f"Model role {role!r} has no configured candidates.")
        return candidates

    def model_for_role(self, role: str) -> ModelRoute:
        """Return the primary model route for a capability role."""
        return self.role_candidates(role)[0]

    def planner_model(self) -> ModelRoute:
        """Return the model shown as the visible orchestrator/planner model."""
        return self.model_for_role("planner")

    def switch_role(self, role: str) -> tuple[str, str]:
        """Switch active model to the primary candidate for a capability role."""
        route = self.model_for_role(role)
        return self.switch(route.provider, route.model)

    def switch(self, provider_name: str, model_name: str | None = None) -> tuple[str, str]:
        """Switch the active provider/model, persisting the choice for next time."""
        from ..core import context as ctx_store

        if provider_name not in self.env_config.providers:
            raise UnknownProviderError(
                f"Unknown provider {provider_name!r}. Available: "
                f"{', '.join(self.env_config.providers)}"
            )
        provider = self.env_config.providers[provider_name]
        if model_name is None:
            model_name = provider.models[0]
        elif model_name not in provider.models:
            raise UnknownModelError(
                f"Model {model_name!r} is not configured for provider {provider_name!r}. "
                f"Available: {', '.join(provider.models)}"
            )

        self._provider_name = provider_name
        self._model_name = model_name
        ctx_store.set_user_preference(
            self.project_dir, "model_settings", {"provider": provider_name, "model": model_name}
        )
        return provider_name, model_name

    def provider_config(self, provider_name: str | None = None) -> ProviderConfig:
        return self.env_config.providers[provider_name or self._provider_name]

    def chat_model(self, **kwargs) -> ChatOpenAI:
        """Build a fresh ChatOpenAI bound to the currently active provider/model."""
        provider = self.provider_config()
        return build_chat_model(provider, self._model_name, **kwargs)
