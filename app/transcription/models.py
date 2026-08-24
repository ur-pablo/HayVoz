"""Validated contracts shared by transcription and persistence."""

from __future__ import annotations

from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class WhisperModelName(StrEnum):
    TINY = "tiny"
    BASE = "base"
    SMALL = "small"
    MEDIUM = "medium"


class Speaker(StrEnum):
    INTERVIEWER = "interviewer"
    INTERVIEWEE = "interviewee"
    UNKNOWN = "unknown"


class SegmentContent(BaseModel):
    """Portable transcript fields written to transcript.json."""

    model_config = ConfigDict(extra="forbid")

    speaker: Speaker
    start: float = Field(ge=0)
    end: float = Field(ge=0)
    text: str = Field(min_length=1)
    confidence: float | None = Field(default=None, ge=0, le=1)

    @field_validator("text")
    @classmethod
    def normalize_text(cls, text: str) -> str:
        normalized = " ".join(text.split())
        if not normalized:
            raise ValueError("El texto del segmento no puede estar vacío.")
        return normalized

    @model_validator(mode="after")
    def validate_timestamps(self) -> SegmentContent:
        if self.end < self.start:
            raise ValueError("El fin del segmento no puede preceder al inicio.")
        return self


class TranscriptSegment(SegmentContent):
    """Persisted transcript segment entity."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    session_id: str = Field(min_length=1)

    def content(self) -> SegmentContent:
        return SegmentContent.model_validate(
            self.model_dump(include={"speaker", "start", "end", "text", "confidence"})
        )


class TranscriptionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    segments: list[SegmentContent]
    language: str | None = None
    language_probability: float | None = Field(default=None, ge=0, le=1)
