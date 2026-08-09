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
