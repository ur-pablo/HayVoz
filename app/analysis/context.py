"""Pure construction of provider-neutral interview context."""

from __future__ import annotations

from app.llm.contracts import AnalysisRequest, TranscriptTurn
from app.sessions.models import Session
from app.transcription.models import TranscriptSegment


def build_analysis_request(
    session: Session,
    segments: list[TranscriptSegment],
) -> AnalysisRequest:
    return AnalysisRequest(
        session_id=session.id,
        title=session.title,
        turns=[
            TranscriptTurn(
                speaker=segment.speaker.value,
                start=segment.start,
                end=segment.end,
                text=segment.text,
            )
            for segment in segments
        ],
    )


def transcript_character_count(request: AnalysisRequest) -> int:
    return sum(len(turn.text) for turn in request.turns)
