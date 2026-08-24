import json
from types import SimpleNamespace

import pytest

pytest.importorskip("openai")

from app.llm.contracts import AnalysisRequest, AssistantRequest, TranscriptTurn
from app.llm.openai_provider import OpenAIProvider
from app.llm.provider import LLMProviderError


class FakeResponses:
    def __init__(self, output_text: str) -> None:
        self.output_text = output_text
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(output_text=self.output_text)


def _request() -> AnalysisRequest:
    return AnalysisRequest(
        session_id="session-1",
        title="Prueba",
        turns=[
            TranscriptTurn(
                speaker="interviewer",
                start=0,
                end=2,
                text="¿Cómo trabajan hoy?",
            )
        ],
    )


def _payload() -> str:
    return json.dumps(
        {
            "summary": "Resumen",
            "notes": [],
            "decisions": [],
            "pain_points": [],
            "actions": [],
            "contradictions": [],
            "follow_up_questions": ["¿Por qué?"],
            "final_report": "# Informe",
        }
    )


def test_openai_provider_sends_only_text_with_structured_output() -> None:
    responses = FakeResponses(_payload())
    client = SimpleNamespace(responses=responses)
    provider = OpenAIProvider(
        api_key="test-key",
        model="configured-model",
        client=client,
    )

    result = provider.analyze(_request())

    assert result.summary == "Resumen"
    assert len(responses.calls) == 1
    call = responses.calls[0]
    assert call["model"] == "configured-model"
    assert call["store"] is False
    assert call["text"]["format"]["type"] == "json_schema"
    assert call["text"]["format"]["strict"] is True
    assert "¿Cómo trabajan hoy?" in call["input"]
    assert "audio" not in call
    assert "tools" not in call


def test_openai_provider_rejects_malformed_response() -> None:
    client = SimpleNamespace(responses=FakeResponses("not-json"))
    provider = OpenAIProvider(api_key="test-key", model="model", client=client)

    with pytest.raises(LLMProviderError, match="contrato esperado"):
        provider.analyze(_request())


def test_openai_provider_builds_stateless_assistant_request() -> None:
    payload = json.dumps(
        {
            "rolling_summary": "Resumen",
            "asked_guide_questions": ["Pregunta uno"],
            "pending_guide_questions": ["Pregunta dos"],
            "suggested_question": "¿Puedes profundizar?",
            "rationale": "La respuesta fue ambigua.",
        }
    )
    responses = FakeResponses(payload)
    provider = OpenAIProvider(
        api_key="test-key",
        model="configured-model",
        client=SimpleNamespace(responses=responses),
    )
    request = AssistantRequest(
        session_id="session-1",
        title="Discovery",
        interview_guide="# Guía\n- Pregunta uno",
        accumulated_summary="Contexto anterior",
        recent_turns=_request().turns,
        previous_suggestions=["¿Pregunta previa?"],
    )

    result = provider.suggest_follow_up(request)

    assert result.suggested_question == "¿Puedes profundizar?"
    call = responses.calls[0]
    assert call["store"] is False
    assert call["text"]["format"]["name"] == "assistant_suggestion"
    assert "Contexto anterior" in call["input"]
    assert "¿Pregunta previa?" in call["input"]
