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

_THINKING_MODEL_MARKERS = ("gpt-oss-120b", "nemotron")


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
                "and/or NVIDIA_API_KEY or OPENROUTER_API_KEY in .env."
            )

        preferences = ctx_store.load(self.project_dir).get("user_preferences", {})
        saved = preferences.get("model_settings", {})
        provider_name = saved.get("provider") or self.env_config.default_provider
        if provider_name not in self.env_config.providers:
            provider_name = next(iter(self.env_config.providers))
        model_name = saved.get("model") or self.env_config.providers[provider_name].models[0]
        if model_name not in self.env_config.providers[provider_name].models:
            model_name = self.env_config.providers[provider_name].models[0]

        self._provider_name = provider_name
        self._model_name = model_name

        default_thinking = self.model_for_role("planner")
        thinking_by_label = {route.label: route for route in self.thinking_candidates()}
        saved_thinking = preferences.get("thinking_model_settings", {})
        saved_label = (
            f"{saved_thinking.get('provider')}:{saved_thinking.get('model')}"
            if saved_thinking.get("provider") and saved_thinking.get("model")
            else ""
        )
        self._thinking_route = thinking_by_label.get(saved_label, default_thinking)

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

    def reload_env(self) -> dict[str, tuple[str, ...]]:
        """Reload provider/model inventory while preserving valid selections."""
        from ..core import context as ctx_store

        refreshed = load_env(self.project_dir)
        if not refreshed.providers:
            raise RuntimeError(
                "No model providers configured. Add provider credentials and models to .env."
            )

        previous_thinking = self._thinking_route
        previous_active = (self._provider_name, self._model_name)
        self.env_config = refreshed

        thinking_by_key = {
            (route.provider, route.model): route for route in self.thinking_candidates()
        }
        thinking_key = (previous_thinking.provider, previous_thinking.model)
        self._thinking_route = thinking_by_key.get(
            thinking_key,
            self.model_for_role("planner"),
        )
        if thinking_key not in thinking_by_key:
            ctx_store.set_user_preference(
                self.project_dir,
                "thinking_model_settings",
                {
                    "provider": self._thinking_route.provider,
                    "model": self._thinking_route.model,
                },
            )

        active_provider = self.env_config.providers.get(previous_active[0])
        if active_provider is None or previous_active[1] not in active_provider.models:
            self._provider_name = self._thinking_route.provider
            self._model_name = self._thinking_route.model
            ctx_store.set_user_preference(
                self.project_dir,
                "model_settings",
                {"provider": self._provider_name, "model": self._model_name},
            )
        return self.list_available()

    def list_visible_models(self) -> dict[str, tuple[str, ...]]:
        """Return only eligible thinking models for user-facing model lists."""
        visible: dict[str, list[str]] = {}
        for route in self.thinking_candidates():
            visible.setdefault(route.provider, []).append(route.model)
        return {provider: tuple(models) for provider, models in visible.items()}

    def thinking_candidates(self) -> tuple[ModelRoute, ...]:
        """Return planner, OSS-120B, and Nemotron routes configured by the user."""
        candidates = [self.model_for_role("planner")]
        candidates.extend(
            ModelRoute(provider_name, model_name)
            for provider_name, provider in self.env_config.providers.items()
            for model_name in provider.models
            if any(marker in model_name.lower() for marker in _THINKING_MODEL_MARKERS)
        )
        seen: set[tuple[str, str]] = set()
        deduped: list[ModelRoute] = []
        for route in candidates:
            key = (route.provider, route.model)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(route)
        return tuple(deduped)

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
        """Return the currently selected thinking/orchestrator model."""
        return self._thinking_route

    def switch_role(self, role: str) -> tuple[str, str]:
        """Switch active model to the primary candidate for a capability role."""
        route = self.planner_model() if role == "planner" else self.model_for_role(role)
        return self.switch(route.provider, route.model)

    def switch_thinking_model(self, provider_name: str, model_name: str) -> tuple[str, str]:
        """Select and persist an eligible model as the team-lead router."""
        from ..core import context as ctx_store

        routes = {(route.provider, route.model): route for route in self.thinking_candidates()}
        try:
            route = routes[(provider_name, model_name)]
        except KeyError as exc:
            raise UnknownModelError(
                f"{provider_name}:{model_name} is not an eligible thinking model."
            ) from exc
        self._thinking_route = route
        ctx_store.set_user_preference(
            self.project_dir,
            "thinking_model_settings",
            {"provider": provider_name, "model": model_name},
        )
        return self.switch(provider_name, model_name)

    def reset_thinking_model(self) -> tuple[str, str]:
        """Restore the role-configured planner as the thinking model."""
        route = self.model_for_role("planner")
        return self.switch_thinking_model(route.provider, route.model)

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

    def chat_model_for_route(self, route: ModelRoute, **kwargs) -> ChatOpenAI:
        """Build a model for ``route`` without changing or persisting active state."""
        candidates = self.env_config.providers.get(route.provider)
        if candidates is None:
            raise UnknownProviderError(f"Unknown provider {route.provider!r}")
        if route.model not in candidates.models:
            raise UnknownModelError(
                f"Model {route.model!r} is not configured for provider {route.provider!r}."
            )
        return build_chat_model(candidates, route.model, **kwargs)
