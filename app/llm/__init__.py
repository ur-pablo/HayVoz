"""Optional external text-intelligence contracts.

This package intentionally does not import a concrete provider at package import
time. Core modules may use the provider-neutral contracts without importing the
OpenAI SDK or provider implementation.
"""

from app.llm.contracts import (
    AnalysisBundle,
    AnalysisRequest,
    AssistantRequest,
    AssistantSuggestion,
    TranscriptTurn,
)
from app.llm.provider import LLMProvider, LLMProviderError

__all__ = [
    "AnalysisBundle",
    "AnalysisRequest",
    "AssistantRequest",
    "AssistantSuggestion",
    "LLMProvider",
    "LLMProviderError",
    "TranscriptTurn",
]


def __getattr__(name: str):
    """Keep the historical OpenAIProvider import lazy for compatibility."""
    if name == "OpenAIProvider":
        from app.llm.openai_provider import OpenAIProvider

        return OpenAIProvider
    raise AttributeError(name)


__all__.append("OpenAIProvider")
