"""Orchestrates reviewed text analysis independently from recording."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from app.analysis.models import Analysis, AnalysisType
from app.core.session_context import SessionContextError, SessionContextService
from app.llm.contracts import AnalysisBundle, AnalysisRequest
from app.llm.provider import LLMProvider, LLMProviderError
from app.storage.analysis_repository import AnalysisRepository

logger = logging.getLogger(__name__)


class AnalysisServiceError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class AnalysisPreview:
    request: AnalysisRequest
    local_only: bool
    character_count: int

    @property
    def segment_count(self) -> int:
        return len(self.request.turns)


class AnalysisService:
    def __init__(
        self,
        context: SessionContextService,
        analyses: AnalysisRepository,
        provider: LLMProvider | None = None,
    ) -> None:
        self.context = context
        self.analyses = analyses
        self.provider = provider

    def preview(self, session_id: str) -> AnalysisPreview:
        try:
            session = self.context.get_session(session_id)
            segments = self.context.get_transcript(session_id)
        except SessionContextError as error:
            raise AnalysisServiceError(str(error)) from error
        if not segments:
            raise AnalysisServiceError(
                "La sesión no tiene transcripción. Ejecuta primero 'hayvoz transcribe'."
            )
        request = AnalysisRequest(
            session_id=session["id"],
            title=session["title"],
            turns=[
                {
                    "speaker": segment["speaker"],
                    "start": segment["start"],
                    "end": segment["end"],
                    "text": segment["text"],
                }
                for segment in segments
            ],
        )
        return AnalysisPreview(
            request=request,
            local_only=session["local_only"],
            character_count=sum(len(turn.text) for turn in request.turns),
        )

    def analyze(
        self, session_id: str, *, allow_external: bool = False
    ) -> list[Analysis]:
        preview = self.preview(session_id)
        if not allow_external:
            raise AnalysisServiceError(
                "La llamada externa requiere confirmación explícita."
            )
        if preview.local_only:
            raise AnalysisServiceError(
                "La sesión fue creada con --local-only y no puede enviarse al "
                "proveedor de IA."
            )
        if self.provider is None:
            raise AnalysisServiceError("No hay un proveedor de IA configurado.")

        logger.info(
            "external_text_request",
            extra={
                "event": "external_text_request",
                "session_id": session_id,
                "provider": self.provider.provider_name,
                "model": self.provider.model,
                "purpose": "interview_analysis",
                "segment_count": preview.segment_count,
                "character_count": preview.character_count,
            },
        )
        try:
            bundle = self.provider.analyze(preview.request)
        except LLMProviderError as error:
            raise AnalysisServiceError(str(error)) from error

        persisted = _to_analyses(session_id, self.provider.model, bundle)
        self.analyses.replace_for_session(session_id, persisted)
        logger.info(
            "analysis_persisted",
            extra={
                "event": "analysis_persisted",
                "session_id": session_id,
                "provider": self.provider.provider_name,
                "model": self.provider.model,
                "status": "completed",
            },
        )
        return persisted


def _to_analyses(
    session_id: str,
    model: str,
    bundle: AnalysisBundle,
) -> list[Analysis]:
    values: list[tuple[AnalysisType, str | list[str]]] = [
        (AnalysisType.SUMMARY, bundle.summary),
        (AnalysisType.NOTES, bundle.notes),
        (AnalysisType.DECISIONS, bundle.decisions),
        (AnalysisType.PAIN_POINTS, bundle.pain_points),
        (AnalysisType.ACTIONS, bundle.actions),
        (AnalysisType.CONTRADICTIONS, bundle.contradictions),
        (AnalysisType.FOLLOW_UP_QUESTIONS, bundle.follow_up_questions),
        (AnalysisType.FINAL_REPORT, bundle.final_report),
    ]
    return [
        Analysis(
            session_id=session_id,
            type=analysis_type,
            content=(
                json.dumps(content, ensure_ascii=False)
                if isinstance(content, list)
                else content
            ),
            model=model,
        )
        for analysis_type, content in values
    ]
