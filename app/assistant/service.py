"""Sequential incremental transcription and debounced follow-up analysis."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from app.assistant.models import AssistantUpdate
from app.llm.contracts import AssistantRequest, TranscriptTurn
from app.llm.provider import LLMProvider, LLMProviderError
from app.sessions.guide import InterviewGuideError, InterviewGuideStore
from app.sessions.models import Session, SessionMode
from app.storage.assistant_repository import AssistantRepository
from app.storage.repository import SessionNotFoundError, SessionRepository
from app.storage.transcript_repository import TranscriptRepository
from app.transcription.json_store import TranscriptJsonStore
from app.transcription.models import Speaker, TranscriptSegment
from app.transcription.transcriber import Transcriber, TranscriberError

logger = logging.getLogger(__name__)


class AssistantServiceError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class AssistantSnapshot:
    session: Session
    recent_segments: list[TranscriptSegment]
    latest_update: AssistantUpdate | None


class AssistantService:
    def __init__(
        self,
        sessions: SessionRepository,
        transcripts: TranscriptRepository,
        updates: AssistantRepository,
        transcript_json: TranscriptJsonStore,
        guides: InterviewGuideStore,
        transcriber: Transcriber,
        provider: LLMProvider | None,
        language: str | None = None,
    ) -> None:
        self.sessions = sessions
        self.transcripts = transcripts
        self.updates = updates
        self.transcript_json = transcript_json
        self.guides = guides
        self.transcriber = transcriber
        self.provider = provider
        self.language = language

    def process_chunk(
        self,
        session_id: str,
        chunk_path: Path,
        *,
        chunk_index: int,
    ) -> list[TranscriptSegment]:
        session = self._assistant_session(session_id)
        if session.assistant_chunk_seconds is None:
            raise AssistantServiceError(
                "La sesión no tiene duración de chunk configurada."
            )
        try:
            output = self.transcriber.transcribe(
                chunk_path,
                language=self.language,
                speaker=Speaker.INTERVIEWER,
            )
        except TranscriberError as error:
            raise AssistantServiceError(str(error)) from error

        offset = chunk_index * session.assistant_chunk_seconds
        segments = [
            TranscriptSegment(
                session_id=session_id,
                speaker=content.speaker,
                start=round(content.start + offset, 3),
                end=round(content.end + offset, 3),
                text=content.text,
                confidence=content.confidence,
            )
            for content in output.segments
        ]
        if segments:
            self.transcripts.append_for_session(session_id, segments)
            complete = self.transcripts.list_for_session(session_id)
            self.transcript_json.write(session_id, complete)
        logger.info(
            "assistant_chunk_transcribed",
            extra={
                "event": "assistant_chunk_transcribed",
                "session_id": session_id,
                "segment_count": len(segments),
            },
        )
        return segments

    def maybe_suggest(self, session_id: str) -> AssistantUpdate | None:
        session = self._assistant_session(session_id)
        if session.local_only or self.provider is None:
            return None
        if session.assistant_last_segments is None:
            raise AssistantServiceError(
                "La sesión no tiene rolling context configurado."
            )
        if session.assistant_analysis_interval_seconds is None:
            raise AssistantServiceError("La sesión no tiene intervalo configurado.")

        recent = self.transcripts.list_recent_for_session(
            session_id,
            limit=session.assistant_last_segments,
        )
        if not recent:
            return None
        previous = self.updates.latest(session_id)
        through_end = recent[-1].end
        previous_end = previous.through_end if previous else 0.0
        if through_end - previous_end < session.assistant_analysis_interval_seconds:
            return None

        try:
            guide = self.guides.read(session.guide_path)
        except InterviewGuideError as error:
            raise AssistantServiceError(str(error)) from error
        previous_updates = self.updates.list_for_session(session_id, limit=5)
        request = AssistantRequest(
            session_id=session.id,
            title=session.title,
            interview_guide=guide,
            accumulated_summary=previous.rolling_summary if previous else "",
            recent_turns=[
                TranscriptTurn(
                    speaker=segment.speaker.value,
                    start=segment.start,
                    end=segment.end,
                    text=segment.text,
                )
                for segment in recent
            ],
            previous_suggestions=[
                update.suggested_question for update in reversed(previous_updates)
            ],
        )
        character_count = (
            sum(len(turn.text) for turn in request.recent_turns)
            + len(request.accumulated_summary)
            + len(request.interview_guide or "")
        )
        logger.info(
            "external_text_request",
            extra={
                "event": "external_text_request",
                "session_id": session_id,
                "provider": self.provider.provider_name,
                "model": self.provider.model,
                "purpose": "assistant_follow_up",
                "segment_count": len(recent),
                "character_count": character_count,
            },
        )
        try:
            suggestion = self.provider.suggest_follow_up(request)
        except LLMProviderError as error:
            raise AssistantServiceError(str(error)) from error
        total_segments = len(self.transcripts.list_for_session(session_id))
        update = AssistantUpdate(
            session_id=session_id,
            rolling_summary=suggestion.rolling_summary,
            asked_questions=suggestion.asked_guide_questions,
            pending_questions=suggestion.pending_guide_questions,
            suggested_question=suggestion.suggested_question,
            rationale=suggestion.rationale,
            segment_count=total_segments,
            through_end=through_end,
            model=self.provider.model,
        )
        self.updates.add(update)
        return update

    def snapshot(
        self, session_id: str, *, transcript_limit: int = 10
    ) -> AssistantSnapshot:
        session = self._assistant_session(session_id)
        return AssistantSnapshot(
            session=session,
            recent_segments=self.transcripts.list_recent_for_session(
                session_id,
                limit=transcript_limit,
            ),
            latest_update=self.updates.latest(session_id),
        )

    def _assistant_session(self, session_id: str) -> Session:
        try:
            session = self.sessions.get(session_id)
        except SessionNotFoundError as error:
            raise AssistantServiceError(f"No existe la sesión {session_id}.") from error
        if session.mode is not SessionMode.ASSISTANT:
            raise AssistantServiceError("La sesión no está en Assistant mode.")
        return session
