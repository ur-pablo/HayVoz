from __future__ import annotations

from pathlib import Path

from app.audio.recorder import RecorderError, StopResult, system_audio_path_for
from app.llm.contracts import (
    AnalysisBundle,
    AnalysisRequest,
    AssistantRequest,
    AssistantSuggestion,
)
from app.llm.provider import LLMProvider, LLMProviderError
from app.transcription.models import (
    SegmentContent,
    Speaker,
    TranscriptionOutput,
    WhisperModelName,
)
from app.transcription.transcriber import TranscriberError


class FakeRecorder:
    def __init__(
        self, *, fail_on_start: bool = False, write_audio: bool = True
    ) -> None:
        self.fail_on_start = fail_on_start
        self.write_audio = write_audio
        self.active: dict[int, Path] = {}
        self.next_pid = 42000

    def start(
        self,
        audio_path: Path,
        device: str,
        log_path: Path,
        *,
        system_device: str | None = None,
    ) -> int:
        if self.fail_on_start:
            raise RecorderError("fallo simulado")
        if self.write_audio:
            audio_path.parent.mkdir(parents=True, exist_ok=True)
            audio_path.write_bytes(b"fLaC-test")
            if system_device is not None:
                system_audio_path_for(audio_path).write_bytes(b"fLaC-system-test")
        pid = self.next_pid
        self.active[pid] = audio_path
        return pid

    def is_active(self, pid: int | None, audio_path: Path) -> bool:
        return pid is not None and self.active.get(pid) == audio_path

    def stop(self, pid: int, audio_path: Path, *, timeout: float = 10.0) -> StopResult:
        if self.active.pop(pid, None) == audio_path:
            return StopResult(stopped=True)
        return StopResult(stopped=False)


class FakeTranscriber:
    model_name = WhisperModelName.SMALL

    def __init__(
        self,
        *,
        fail: bool = False,
        fail_on_call: int | None = None,
        text: str = "Texto de prueba",
    ) -> None:
        self.fail = fail
        self.fail_on_call = fail_on_call
        self.text = text
        self.calls: list[Path] = []

    def transcribe(
        self,
        audio_path: Path,
        *,
        language: str | None,
        speaker: Speaker,
    ) -> TranscriptionOutput:
        self.calls.append(audio_path)
        if self.fail or self.fail_on_call == len(self.calls):
            raise TranscriberError("fallo Whisper simulado")
        return TranscriptionOutput(
            segments=[
                SegmentContent(
                    speaker=speaker,
                    start=0.5,
                    end=2.25,
                    text=self.text,
                    confidence=0.91,
                )
            ],
            language=language or "es",
            language_probability=0.98,
        )


class FakeLLMProvider(LLMProvider):
    provider_name = "fake"
    model = "test-model"

    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.requests: list[AnalysisRequest] = []
        self.assistant_requests: list[AssistantRequest] = []

    def analyze(self, request: AnalysisRequest) -> AnalysisBundle:
        self.requests.append(request)
        if self.fail:
            raise LLMProviderError("fallo OpenAI simulado")
        return AnalysisBundle(
            summary="Resumen verificable.",
            notes=["Nota uno"],
            decisions=["Decisión uno"],
            pain_points=["Dolor uno"],
            actions=["Acción uno"],
            contradictions=[],
            follow_up_questions=["¿Qué falta aclarar?"],
            final_report="# Informe final\n\nContenido verificable.",
        )

    def suggest_follow_up(self, request: AssistantRequest) -> AssistantSuggestion:
        self.assistant_requests.append(request)
        if self.fail:
            raise LLMProviderError("fallo OpenAI simulado")
        return AssistantSuggestion(
            rolling_summary="Resumen acumulado.",
            asked_guide_questions=["¿Cómo trabajan hoy?"],
            pending_guide_questions=["¿Qué cambiarían?"],
            suggested_question="¿Qué impacto tiene ese problema?",
            rationale="Profundiza el pain point sin repetir la guía.",
        )

    def summarize(self, request: AnalysisRequest) -> str:
        return self.analyze(request).summary
