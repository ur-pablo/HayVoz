"""Persisted Assistant state."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class AssistantUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: str(uuid4()))
    session_id: str = Field(min_length=1)
    rolling_summary: str = Field(min_length=1)
    asked_questions: list[str]
    pending_questions: list[str]
    suggested_question: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    segment_count: int = Field(ge=1)
    through_end: float = Field(gt=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    model: str = Field(min_length=1)
