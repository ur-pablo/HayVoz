"""Persisted analysis domain models."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class AnalysisType(StrEnum):
    SUMMARY = "summary"
    NOTES = "notes"
    DECISIONS = "decisions"
    PAIN_POINTS = "pain_points"
    ACTIONS = "actions"
    CONTRADICTIONS = "contradictions"
    FOLLOW_UP_QUESTIONS = "follow_up_questions"
    FINAL_REPORT = "final_report"


class Analysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: str(uuid4()))
    session_id: str = Field(min_length=1)
    type: AnalysisType
    content: str = Field(min_length=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    model: str = Field(min_length=1)
