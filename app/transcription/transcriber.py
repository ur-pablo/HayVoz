"""Local faster-whisper adapter with bounded CPU concurrency."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Protocol

from app.config import Settings
from app.transcription.model_manager import WhisperModelManager
from app.transcription.models import (
    SegmentContent,
    Speaker,
    TranscriptionOutput,
    WhisperModelName,
)


class TranscriberError(RuntimeError):
    pass


class Transcriber(Protocol):
    model_name: WhisperModelName

    def transcribe(
        self,
        audio_path: Path,
        *,
        language: str | None,
        speaker: Speaker,
    ) -> TranscriptionOutput: ...


class FasterWhisperTranscriber:
    """One model instance and one sequential transcription per command."""

    def __init__(
        self,
        settings: Settings,
        model_name: WhisperModelName,
        *,
        vad: bool | None = None,
    ) -> None:
        self.settings = settings
        self.model_name = model_name
        self.vad = settings.whisper_vad if vad is None else vad
        self._model: object | None = None

    def transcribe(
        self,
        audio_path: Path,
        *,
        language: str | None,
        speaker: Speaker,
    ) -> TranscriptionOutput:
        model_path = WhisperModelManager(self.settings).path_for(self.model_name)
        if not WhisperModelManager(self.settings).is_installed(self.model_name):
            raise TranscriberError(
                f"El modelo {self.model_name.value} no está instalado. Ejecuta: "
                f"hayvoz model download --model {self.model_name.value}"
            )
        try:
            model = self._load_model(model_path)
            generated, info = model.transcribe(  # type: ignore[attr-defined]
                str(audio_path),
                language=language,
                beam_size=self.settings.whisper_beam_size,
                best_of=1,
                temperature=0.0,
                vad_filter=self.vad,
                word_timestamps=False,
                without_timestamps=False,
            )
            segments: list[SegmentContent] = []
            for segment in generated:
                text = " ".join(segment.text.split())
                if not text:
                    continue
                segments.append(
                    SegmentContent(
                        speaker=speaker,
                        start=round(float(segment.start), 3),
                        end=round(float(segment.end), 3),
                        text=text,
                        confidence=_confidence(segment.avg_logprob),
                    )
                )
            return TranscriptionOutput(
                segments=segments,
                language=getattr(info, "language", language),
                language_probability=_optional_probability(
                    getattr(info, "language_probability", None)
                ),
            )
        except TranscriberError:
            raise
        except Exception as error:
            raise TranscriberError(
                f"Whisper no pudo transcribir el audio: {error}"
            ) from error

    def _load_model(self, model_path: Path) -> object:
        if self._model is not None:
            return self._model
        try:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(
                str(model_path),
                device="cpu",
                compute_type="int8",
                cpu_threads=self.settings.whisper_cpu_threads,
                num_workers=1,
                local_files_only=True,
            )
        except Exception as error:
            raise TranscriberError(
                f"No se pudo cargar Whisper en CPU int8: {error}"
            ) from error
        return self._model


def _confidence(avg_logprob: float | None) -> float | None:
    if avg_logprob is None:
        return None
    return round(max(0.0, min(1.0, math.exp(float(avg_logprob)))), 4)


def _optional_probability(value: float | None) -> float | None:
    if value is None:
        return None
    return round(max(0.0, min(1.0, float(value))), 4)
