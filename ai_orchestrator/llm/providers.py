"""Build LangChain chat models from provider configuration.

The configured providers (including Lightning, NVIDIA NIM, and OpenRouter)
speak the OpenAI chat-completions protocol, so a single
``ChatOpenAI`` wrapper covers them — only the provider configuration differs.
"""

from __future__ import annotations

from langchain_openai import ChatOpenAI

from ..config import ProviderConfig


def build_chat_model(
    provider: ProviderConfig,
    model: str,
    *,
    temperature: float | None = None,
    timeout: float = 120.0,
    max_retries: int | None = None,
) -> ChatOpenAI:
    """Construct a ``ChatOpenAI`` instance pointed at the given provider/model.

    ``temperature``/``max_retries`` default to the provider's configured values
    (``<PROVIDER>_TEMPERATURE``/``<PROVIDER>_MAX_RETRIES``, or the global
    ``DEFAULT_TEMPERATURE``/``DEFAULT_MAX_RETRIES``, in ``.env``) — pass
    explicit values here to override for a single call.

    Retries transient failures (timeouts, connection resets, 5xx) before
    giving up — small self-hosted GPU instances are more prone to cold-starts/
    blips than a major hosted API.
    """
    kwargs: dict[str, object] = {}
    if provider.default_headers:
        kwargs["default_headers"] = dict(provider.default_headers)

    return ChatOpenAI(
        base_url=provider.base_url,
        api_key=provider.api_key,
        model=model,
        temperature=temperature if temperature is not None else provider.temperature,
        timeout=timeout,
        max_retries=max_retries if max_retries is not None else provider.max_retries,
        **kwargs,
    )
