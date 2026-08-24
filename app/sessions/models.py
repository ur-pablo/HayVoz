"""Phase 1 session domain model."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path


class SessionMode(StrEnum):
    RECORD = "record"
    ASSISTANT = "assistant"


class SessionStatus(StrEnum):
    STARTING = "starting"
    RECORDING = "recording"
    STOPPING = "stopping"
    COMPLETED = "completed"
    INTERRUPTED = "interrupted"
    FAILED = "failed"


ACTIVE_STATUSES = (
    SessionStatus.STARTING,
    SessionStatus.RECORDING,
    SessionStatus.STOPPING,
)


@dataclass(frozen=True, slots=True)
class Session:
    id: str
    title: str
    created_at: datetime
    started_at: datetime | None
    ended_at: datetime | None
    mode: SessionMode
    status: SessionStatus
    audio_path: Path
    system_audio_path: Path | None = None
    system_audio_device: str | None = None
    guide_path: Path | None = None
    assistant_chunk_seconds: int | None = None
    assistant_analysis_interval_seconds: int | None = None
    assistant_last_segments: int | None = None
    recording_pid: int | None = None
    local_only: bool = False
    error_message: str | None = None
