"""Abstract boundary for generative text reasoning."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.llm.contracts import (
    AnalysisBundle,
    AnalysisRequest,
    AssistantRequest,
    AssistantSuggestion,
)


class LLMProviderError(RuntimeError):
    pass


class LLMProvider(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def model(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def analyze(self, request: AnalysisRequest) -> AnalysisBundle:
        raise NotImplementedError

    @abstractmethod
    def suggest_follow_up(self, request: AssistantRequest) -> AssistantSuggestion:
        raise NotImplementedError

    @abstractmethod
    def summarize(self, request: AnalysisRequest) -> str:
        raise NotImplementedError
