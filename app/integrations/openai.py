"""Optional OpenAI integration entry point.

The module is not imported by local capture, transcription, storage, or context
flows. The OpenAI SDK is imported lazily by the existing provider implementation.
"""

from app.config import Settings
from app.llm.factory import create_provider as _create_provider
from app.llm.provider import LLMProvider


def create_provider(settings: Settings) -> LLMProvider:
    """Create the optional configured OpenAI provider."""
    return _create_provider(settings)
