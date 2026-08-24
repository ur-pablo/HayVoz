"""Small locale capability layer without translating the whole interface."""

from __future__ import annotations

import locale
import re

DEFAULT_LANGUAGE = "en"
ASSISTANT_TERMS = {
    "de": "Assistent",
    "en": "Assistant",
    "es": "Asistente",
    "fr": "Assistant",
    "it": "Assistente",
    "pt": "Assistente",
}


def normalize_language(value: str | None) -> str:
    """Return a supported two-letter language code with a safe fallback."""
    if not value:
        return DEFAULT_LANGUAGE
    match = re.match(r"[A-Za-z]{2}", value.strip())
    language = match.group(0).lower() if match else DEFAULT_LANGUAGE
    return language if language in ASSISTANT_TERMS else DEFAULT_LANGUAGE


def system_language() -> str:
    """Resolve the operating-system locale without mutating process locale."""
    language, _encoding = locale.getlocale()
    return normalize_language(language)


def assistant_term(language: str | None = None) -> str:
    return ASSISTANT_TERMS[normalize_language(language or system_language())]


def assistant_aliases() -> tuple[str, ...]:
    """Return stable lowercase command aliases without duplicates."""
    return tuple(dict.fromkeys(term.casefold() for term in ASSISTANT_TERMS.values()))
