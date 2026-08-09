"""Domain text-turn pipeline with stub LLM and fake retrieval."""

from __future__ import annotations

from limen.clinical.state import ClinicalState, Finding
from limen.clinical.uncertainty import ClinicalCertainty
from limen.conversation.orchestrator import ConversationOrchestrator
from limen.conversation.response import FALLBACK_TEMPLATE
from limen.intelligence.contracts import LLMRequest, LLMResponse
from limen.intelligence.providers.stub import StubLLMProvider
from limen.knowledge.contracts import EvidenceChunk
from limen.safety.decision import Severity


class _FakeRetrieval:
    def __init__(self, chunks: list[EvidenceChunk] | None = None) -> None:
        self.calls = 0
        self._chunks = chunks or [
            EvidenceChunk(
                document_id="doc-1",
                chunk_id="chunk-1",
                text="Vigilar fiebre y signos de infección en la herida.",
                source_name="protocolo.txt",
                page=1,
                score=1.0,
            )
        ]

    def retrieve(self, *, account_id: str, query: str, limit: int = 5) -> list[EvidenceChunk]:
        self.calls += 1
        return list(self._chunks)[:limit]


class _FailingLLM:
    async def generate_text(self, request: LLMRequest) -> LLMResponse:
        raise RuntimeError("llm_unavailable")

    async def generate_structured(self, request: LLMRequest, schema: type):  # noqa: ANN401
        raise RuntimeError("llm_unavailable")


async def test_pipeline_extract_uncertainty_retrieve_floor_response() -> None:
    retrieval = _FakeRetrieval()
    orch = ConversationOrchestrator(retrieval=retrieval, llm=StubLLMProvider())
    result = await orch.handle_text_turn(
        call_id="call-1",
        account_id="acct-1",
        user_text="tengo fiebre y dolor en la herida",
        clinical_state=ClinicalState(),
    )
    assert any(f.name == "fever" for f in result.clinical_state.findings)
    assert result.uncertainty is not None
    assert result.uncertainty.should_retrieve is True
    assert retrieval.calls == 1
    assert len(result.evidence) == 1
    assert result.safety.severity == Severity.YELLOW
    assert result.safety.escalate is False
    assert result.assistant_text
    assert result.metrics["rag_queries"] == 1
    assert result.metrics["estimated_cost_usd"] is None


async def test_pipeline_skips_retrieval_naturally_without_findings() -> None:
    """Without synthetic open questions, benign text must not force retrieval."""
    retrieval = _FakeRetrieval()
    orch = ConversationOrchestrator(retrieval=retrieval, llm=StubLLMProvider())
    result = await orch.handle_text_turn(
        call_id="call-2",
        account_id="acct-1",
        user_text="hola, gracias",
        clinical_state=ClinicalState(),
    )
    assert result.clinical_state.findings == []
    assert result.uncertainty is not None
    assert result.uncertainty.should_retrieve is False
    assert retrieval.calls == 0
    assert result.metrics["rag_queries"] == 0
    assert result.evidence == []


async def test_pipeline_opening_greeting_not_clinical_boilerplate() -> None:
    """Phatic first turn must not dump GREEN recovery + no-evidence hedging."""
    from limen.conversation.context import ConversationContext

    orch = ConversationOrchestrator(retrieval=_FakeRetrieval(), llm=None)
    result = await orch.handle_text_turn(
        call_id="call-greet",
        account_id="acct-1",
        user_text="Muy buenas tardes.",
        clinical_state=ClinicalState(),
        conversation=ConversationContext(
            call_id="call-greet",
            assistant_display_name="Anikka",
            assistant_gender="female",
        ),
    )
    assert "recuperación esperada" not in result.assistant_text
    assert "documentación adicional" not in result.assistant_text
    assert "Anikka" in result.assistant_text or "LIMEN" in result.assistant_text
    assert result.response_meta.get("response_source") == "opening_template"


async def test_pipeline_hola_anika_is_assistant_not_patient() -> None:
    from limen.conversation.context import ConversationContext

    orch = ConversationOrchestrator(retrieval=_FakeRetrieval(), llm=StubLLMProvider())
    result = await orch.handle_text_turn(
        call_id="call-anika",
        account_id="acct-1",
        user_text="Hola, Anika.",
        clinical_state=ClinicalState(),
        conversation=ConversationContext(
            call_id="call-anika",
            assistant_display_name="Anikka",
            assistant_gender="female",
            assistant_persona_id="anikka",
        ),
    )
    assert result.response_meta.get("response_source") == "opening_template"
    assert "Soy Anikka" in result.assistant_text
    assert ", Anika" not in result.assistant_text
    assert result.conversation is not None
    assert result.conversation.patient_display_name is None


async def test_pipeline_terminar_reunion_ends_session() -> None:
    from limen.conversation.context import ConversationContext

    orch = ConversationOrchestrator(retrieval=_FakeRetrieval(), llm=StubLLMProvider())
    result = await orch.handle_text_turn(
        call_id="call-bye",
        account_id="acct-1",
        user_text="Quiero terminar la reunión.",
        clinical_state=ClinicalState(),
        conversation=ConversationContext(
            call_id="call-bye",
            assistant_display_name="Anikka",
            greeting_done=True,
        ),
    )
    assert result.response_meta.get("response_source") == "farewell_template"
    assert result.response_meta.get("end_session") is True
    assert result.response_meta.get("call_end_reason") == "patient_farewell"
    assert "Hasta pronto" in result.assistant_text


async def test_pipeline_retrieves_for_knowledge_protocol_question() -> None:
    """G5-style admin/protocol questions must retrieve even with empty clinical state."""
    retrieval = _FakeRetrieval(
        [
            EvidenceChunk(
                document_id="doc-g5",
                chunk_id="chunk-g5",
                text="El marcador administrativo es LUNA-73 (protocolo ZXQ-921).",
                source_name="g5.txt",
                page=1,
                score=0.9,
            )
        ]
    )
    orch = ConversationOrchestrator(retrieval=retrieval, llm=StubLLMProvider())
    result = await orch.handle_text_turn(
        call_id="call-g5",
        account_id="acct-1",
        user_text="¿Cuál es el marcador administrativo del protocolo ZXQ-921?",
        clinical_state=ClinicalState(),
    )
    assert result.clinical_state.findings == []
    assert result.uncertainty is not None
    assert result.uncertainty.should_retrieve is False
    assert retrieval.calls == 1
    assert result.metrics["rag_queries"] == 1
    assert len(result.evidence) == 1
    assert "LUNA-73" in result.evidence[0].text


async def test_escalation_uses_template_not_llm() -> None:
    orch = ConversationOrchestrator(llm=StubLLMProvider())
    result = await orch.handle_text_turn(
        call_id="call-3",
        account_id="acct-1",
        user_text="no puedo respirar",
        clinical_state=ClinicalState(),
    )
    assert result.safety.escalate is True
    assert result.metrics["llm_calls"] == 0
    assert "urgencia" in result.assistant_text.lower()


async def test_conflicting_finding_through_real_pipeline() -> None:
    retrieval = _FakeRetrieval()
    prior = ClinicalState(
        findings=[
            Finding(name="wound", certainty=ClinicalCertainty.CONFLICTING, notes="reports differ"),
        ],
    )
    orch = ConversationOrchestrator(retrieval=retrieval, llm=StubLLMProvider())
    result = await orch.handle_text_turn(
        call_id="call-4",
        account_id="acct-1",
        user_text="sigo sin claridad sobre la herida",
        clinical_state=prior,
    )
    wound = next(f for f in result.clinical_state.findings if f.name == "wound")
    assert wound.certainty == ClinicalCertainty.CONFLICTING
    assert result.uncertainty is not None
    assert "wound" in result.uncertainty.conflicting
    assert result.uncertainty.should_retrieve is True
    assert retrieval.calls == 1
    assert any("herida" in q.lower() for q in result.clinical_state.open_questions)


async def test_provider_failure_does_not_change_safety_or_crash() -> None:
    orch = ConversationOrchestrator(llm=_FailingLLM())
    result = await orch.handle_text_turn(
        call_id="call-5",
        account_id="acct-1",
        user_text="tengo un poco de fiebre",
        clinical_state=ClinicalState(),
    )
    assert result.safety.severity == Severity.YELLOW
    assert result.safety.escalate is False
    assert result.metrics["llm_calls"] == 0
    assert result.assistant_text
    assert result.assistant_text != ""
    # Template fallback — not an empty or invented GREEN downgrade path.
    assert result.assistant_text
    lower = result.assistant_text.lower()
    assert (
        result.assistant_text == FALLBACK_TEMPLATE
        or "revisar" in lower
        or "observe" in lower
        or "seguridad" in lower
        or "documentación" in lower
        or "documentacion" in lower
        or "continúe" in lower
        or "continue" in lower
    )
