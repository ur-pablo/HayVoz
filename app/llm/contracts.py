"""Provider-neutral contracts for text analysis."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class TranscriptTurn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    speaker: str
    start: float = Field(ge=0)
    end: float = Field(gt=0)
    text: str = Field(min_length=1)


class AnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    turns: list[TranscriptTurn] = Field(min_length=1)


class AnalysisBundle(BaseModel):
    """Single structured response used to minimize external calls."""

    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1)
    notes: list[str]
    decisions: list[str]
    pain_points: list[str]
    actions: list[str]
    contradictions: list[str]
    follow_up_questions: list[str]
    final_report: str = Field(min_length=1)


class AssistantRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    interview_guide: str | None = None
    accumulated_summary: str = ""
    recent_turns: list[TranscriptTurn] = Field(min_length=1)
    previous_suggestions: list[str] = Field(default_factory=list)


class AssistantSuggestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rolling_summary: str = Field(min_length=1)
    asked_guide_questions: list[str]
    pending_guide_questions: list[str]
    suggested_question: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
