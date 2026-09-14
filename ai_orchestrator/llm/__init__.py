"""LangChain-backed model access: build chat models, switch providers at runtime."""

from .providers import build_chat_model
from .registry import ModelRegistry, UnknownModelError, UnknownModelRoleError, UnknownProviderError
from .router import QueryRouter, RoutingDecision

__all__ = [
    "build_chat_model",
    "ModelRegistry",
    "UnknownModelError",
    "UnknownModelRoleError",
    "UnknownProviderError",
    "QueryRouter",
    "RoutingDecision",
]
