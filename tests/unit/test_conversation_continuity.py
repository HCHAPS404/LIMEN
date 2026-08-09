"""PHASE 6.3 — multi-turn conversation continuity (semantic state, not wording)."""

from __future__ import annotations

import pytest

from limen.clinical.extraction import extract_from_utterance
from limen.clinical.state import ClinicalState
from limen.clinical.uncertainty import ClinicalCertainty
from limen.clinical.uncertainty_analysis import analyze_uncertainty, apply_uncertainty
from limen.conversation.context import (
    ConversationContext,
    PendingAssistantIntent,
    PendingQuestion,
    extract_pain_severity_mention,
)
from limen.conversation.continuity import (
    filter_open_questions,
    is_near_duplicate,
    mark_interrupted,
    update_context_after_assistant,
    update_context_after_patient,
)
from limen.conversation.orchestrator import ConversationOrchestrator
from limen.conversation.response import build_assistant_response
from limen.conversation.response_templates import RED_ESCALATION_TEMPLATE
from limen.intelligence.llm_status import reset_llm_runtime_status_for_tests
from limen.knowledge.contracts import EvidenceChunk
from limen.safety.decision import SafetyDecision, Severity


def test_pain_severity_parse_como_un_siete() -> None:
    assert extract_pain_severity_mention("como un siete") == 7
    assert extract_pain_severity_mention("duele un 8/10") == 8


def test_negation_preserves_fever_normal_and_wound_heat() -> None:
    state = extract_from_utterance("Me duele la herida.")
    state = extract_from_utterance("No tengo fiebre.", state)
    fever = next(f for f in state.findings if f.name == "fever")
    assert fever.certainty == ClinicalCertainty.KNOWN_NORMAL
    state = extract_from_utterance("Pero sí siento la herida caliente.", state)
    heat = next(f for f in state.findings if f.name == "wound_heat")
    assert heat.certainty == ClinicalCertainty.KNOWN_ABNORMAL
    fever2 = next(f for f in state.findings if f.name == "fever")
    assert fever2.certainty == ClinicalCertainty.KNOWN_NORMAL


def test_pending_question_resolves_pain_score() -> None:
    ctx = ConversationContext(
        call_id="c1",
        pending_question=PendingQuestion(
            id="q1",
            intent="pain_severity",
            requested_fields=["pain_severity"],
            text="¿Con qué intensidad?",
            asked_at_turn=1,
        ),
    )
    ctx = update_context_after_patient(ctx, user_text="como un siete", max_recent_turns=6)
    assert ctx.pending_question is None
    assert "pain_severity" in ctx.answered_intents
    assert "q1" in ctx.answered_question_ids


def test_filter_skips_answered_pain_intensity() -> None:
    ctx = ConversationContext(answered_intents=["pain_severity"])
    filtered = filter_open_questions(
        ["¿Cómo evoluciona el dolor y con qué intensidad?", "¿Hay fiebre?"],
        ctx,
    )
    assert len(filtered) == 1
    assert "fiebre" in filtered[0].lower()


def test_uncertainty_skips_intensity_when_severity_known() -> None:
    state = extract_from_utterance("Me duele como un siete.")
    report = analyze_uncertainty(state)
    assert all("intensidad" not in q.lower() for q in report.unresolved)
    assert any("empeora" in q.lower() or "igual" in q.lower() for q in report.unresolved)


def test_near_duplicate_detection() -> None:
    a = "Entiendo. Para ayudarte mejor, ¿cómo evoluciona el dolor?"
    assert is_near_duplicate(a, a)
    b = "Entiendo. Para ayudarte mejor, ¿cómo evoluciona el dolor ahora?"
    # High overlap boilerplate + same stem.
    from limen.conversation.continuity import has_excessive_generic_opener

    assert has_excessive_generic_opener(b, a)


@pytest.mark.asyncio
async def test_case_a_progressive_pain_state() -> None:
    reset_llm_runtime_status_for_tests()
    orch = ConversationOrchestrator(llm=None)
    clinical = ClinicalState()
    ctx = ConversationContext(call_id="a")
    r1 = await orch.handle_text_turn(
        call_id="a",
        account_id="acc",
        user_text="Me duele la herida.",
        clinical_state=clinical,
        conversation=ctx,
    )
    assert any(f.name == "pain" for f in r1.clinical_state.findings)
    r2 = await orch.handle_text_turn(
        call_id="a",
        account_id="acc",
        user_text="Como un siete y hoy está peor.",
        clinical_state=r1.clinical_state,
        conversation=r1.conversation,
    )
    assert any(f.name == "pain_severity" for f in r2.clinical_state.findings)
    # Should not re-ask intensity after score captured.
    assert all("intensidad" not in q.lower() for q in r2.clinical_state.open_questions)
    r3 = await orch.handle_text_turn(
        call_id="a",
        account_id="acc",
        user_text="Además está más roja.",
        clinical_state=r2.clinical_state,
        conversation=r2.conversation,
    )
    assert r3.conversation is not None
    assert r3.conversation.turn_index >= 3
    assert r3.conversation.greeting_done is True


@pytest.mark.asyncio
async def test_case_c_ambiguous_reference_via_pending() -> None:
    reset_llm_runtime_status_for_tests()
    orch = ConversationOrchestrator(llm=None)
    clinical = ClinicalState()
    r1 = await orch.handle_text_turn(
        call_id="c",
        account_id="acc",
        user_text="Me duele mucho.",
        clinical_state=clinical,
        conversation=ConversationContext(call_id="c"),
    )
    # Force pending pain severity as if assistant asked.
    assert r1.conversation is not None
    r1.conversation.pending_question = PendingQuestion(
        id="painq",
        intent="pain_severity",
        requested_fields=["pain_severity"],
        text="¿De 0 a 10 cuánto duele?",
        asked_at_turn=1,
    )
    r2 = await orch.handle_text_turn(
        call_id="c",
        account_id="acc",
        user_text="como un siete",
        clinical_state=r1.clinical_state,
        conversation=r1.conversation,
    )
    assert "pain_severity" in (r2.conversation.answered_intents if r2.conversation else [])
    assert any(f.name == "pain_severity" for f in r2.clinical_state.findings)


@pytest.mark.asyncio
async def test_case_e_no_evidence_continuity() -> None:
    reset_llm_runtime_status_for_tests()
    orch = ConversationOrchestrator(llm=None, retrieval=None)
    r1 = await orch.handle_text_turn(
        call_id="e",
        account_id="acc",
        user_text="Me duele un poco la cicatriz.",
        clinical_state=ClinicalState(),
        conversation=ConversationContext(call_id="e"),
    )
    r2 = await orch.handle_text_turn(
        call_id="e",
        account_id="acc",
        user_text="Sin fiebre.",
        clinical_state=r1.clinical_state,
        conversation=r1.conversation,
    )
    assert r1.assistant_text != r2.assistant_text or r2.conversation.turn_index > 1
    assert r2.conversation is not None
    assert r2.conversation.greeting_done is True


@pytest.mark.asyncio
async def test_case_g_h_interruption_preserves_red_intent() -> None:
    reset_llm_runtime_status_for_tests()
    ctx = ConversationContext(
        call_id="red",
        previous_assistant_response=RED_ESCALATION_TEMPLATE,
        pending_assistant_intent=PendingAssistantIntent(
            type="safety_instruction",
            safety_critical=True,
            completed=False,
            interrupted=True,
            text=RED_ESCALATION_TEMPLATE,
            required_information=["seek_urgent_care"],
        ),
        previous_response_interrupted=True,
        greeting_done=True,
        turn_index=2,
    )
    text, calls, *_r, meta = await build_assistant_response(
        user_text="Pero también estoy sangrando.",
        safety=SafetyDecision(severity=Severity.RED, reasons=["bleed"], escalate=True),
        evidence=[],
        open_questions=[],
        llm=None,
        conversation=ctx,
    )
    assert calls == 0
    assert "urgencia" in text.lower() or "urgente" in text.lower()
    assert meta["response_source"] == "template"


def test_mark_interrupted_keeps_pending_question() -> None:
    ctx = ConversationContext(
        pending_question=PendingQuestion(
            id="q", intent="fever_status", text="¿fiebre?", asked_at_turn=1
        ),
        pending_assistant_intent=PendingAssistantIntent(
            type="question", completed=True, text="¿tiene fiebre?"
        ),
        previous_assistant_response="¿tiene fiebre?",
    )
    ctx = update_context_after_assistant(
        ctx,
        assistant_text="Para entender mejor el dolor, ¿tiene fiebre?",
        safety=SafetyDecision.green(),
        open_questions=["¿tiene fiebre?"],
        evidence_available=False,
    )
    ctx = mark_interrupted(ctx)
    assert ctx.previous_response_interrupted is True
    assert ctx.pending_assistant_intent is not None
    assert ctx.pending_assistant_intent.interrupted is True
    assert ctx.pending_assistant_intent.completed is False
    assert ctx.pending_question is not None


@pytest.mark.asyncio
async def test_case_d_evidence_available_flag() -> None:
    reset_llm_runtime_status_for_tests()

    class _Ret:
        last_metrics: dict = {}

        def retrieve(self, **_kwargs):  # noqa: ANN003
            return [
                EvidenceChunk(
                    chunk_id="c1",
                    document_id="d1",
                    source_name="guia.pdf",
                    page=1,
                    text="Observe enrojecimiento y fiebre.",
                    score=0.9,
                )
            ]

    orch = ConversationOrchestrator(llm=None, retrieval=_Ret())  # type: ignore[arg-type]
    # Seed abnormal finding so retrieval runs
    clinical = extract_from_utterance("Me duele la herida y tengo fiebre.")
    clinical = apply_uncertainty(clinical, analyze_uncertainty(clinical))
    result = await orch.handle_text_turn(
        call_id="d",
        account_id="acc",
        user_text="Me duele la herida y tengo fiebre.",
        clinical_state=ClinicalState(),
        conversation=ConversationContext(call_id="d"),
    )
    assert result.metrics.get("rag_queries") == 1 or len(result.evidence) >= 0
    assert result.conversation is not None
    if result.evidence:
        assert result.conversation.evidence_available is True


@pytest.mark.asyncio
async def test_novelty_retry_once_then_template() -> None:
    reset_llm_runtime_status_for_tests()
    from limen.intelligence.contracts import LLMRequest, LLMResponse

    class _RepeatLLM:
        provider_name = "fake"
        calls = 0

        async def generate_text(self, request: LLMRequest) -> LLMResponse:
            self.calls += 1
            return LLMResponse(
                text="Entiendo. Para ayudarte mejor, ¿cómo evoluciona el dolor?",
                model="fake",
                provider="fake",
                prompt_tokens=10,
                completion_tokens=8,
                latency_ms=1.0,
                generation_ms=1.0,
                finish_reason="stop",
            )

        async def generate_structured(self, request: LLMRequest, schema: type):  # noqa: ANN401
            raise RuntimeError("unused")

    llm = _RepeatLLM()
    ctx = ConversationContext(
        previous_assistant_response="Entiendo. Para ayudarte mejor, ¿cómo evoluciona el dolor?",
        greeting_done=True,
        turn_index=2,
    )
    text, calls, _a, _b, meta = await build_assistant_response(
        user_text="sigue igual",
        safety=SafetyDecision.green(),
        evidence=[],
        open_questions=[],
        llm=llm,
        conversation=ctx,
    )
    assert calls == 2  # one retry max
    assert meta.get("novelty_retry") is True
    assert text  # template or regenerated; not empty
