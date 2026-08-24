import pytest
from pydantic import ValidationError

from app.transcription.models import SegmentContent, Speaker, TranscriptSegment


def test_parse_and_normalize_transcript_segment() -> None:
    segment = TranscriptSegment.model_validate(
        {
            "session_id": "session-1",
            "speaker": "interviewer",
            "start": 1.25,
            "end": 2.75,
            "text": "  Una   pregunta.  ",
            "confidence": 0.87,
        }
    )
    assert segment.speaker is Speaker.INTERVIEWER
    assert segment.text == "Una pregunta."
    assert segment.content() == SegmentContent(
        speaker="interviewer",
        start=1.25,
        end=2.75,
        text="Una pregunta.",
        confidence=0.87,
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"end": 0.5},
        {"confidence": 1.1},
        {"text": "   "},
    ],
)
def test_reject_invalid_segment(changes: dict[str, object]) -> None:
    payload = {
        "speaker": "interviewee",
        "start": 1.0,
        "end": 2.0,
        "text": "Respuesta",
        "confidence": 0.5,
    }
    payload.update(changes)
    with pytest.raises(ValidationError):
        SegmentContent.model_validate(payload)
