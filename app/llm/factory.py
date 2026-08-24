"""Create the configured AI provider without exposing credentials."""

from __future__ import annotations

from app.config import Settings
from app.llm.openai_provider import OpenAIProvider
from app.llm.provider import LLMProvider, LLMProviderError


def create_provider(settings: Settings) -> LLMProvider:
    if settings.ai_provider not in {"openai", "openai-compatible"}:
        raise LLMProviderError(f"Proveedor de IA no soportado: {settings.ai_provider}.")
    return OpenAIProvider(
        api_key=settings.ai_api_key or "",
        model=settings.ai_model or "",
        timeout_seconds=settings.ai_timeout_seconds,
        base_url=settings.ai_base_url,
        provider_name=settings.ai_provider,
    )
