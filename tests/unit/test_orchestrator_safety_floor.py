from limen.clinical.state import ClinicalState
from limen.conversation.orchestrator import ConversationOrchestrator
from limen.intelligence.providers.stub import StubLLMProvider
from limen.safety.decision import Severity


async def test_red_utterance_escalates_and_cannot_be_green() -> None:
    orchestrator = ConversationOrchestrator(llm=StubLLMProvider())
    result = await orchestrator.handle_text_turn(
        call_id="c1",
        account_id="a1",
        user_text="no puedo respirar y hay sangrado abundante",
        clinical_state=ClinicalState(),
    )
    assert result.safety.severity == Severity.RED
    assert result.safety.escalate is True
    assert "urgencia" in result.assistant_text.lower() or "médica" in result.assistant_text.lower()
    # Generative path must not weaken the floor or call LLM on escalate.
    assert result.metrics["llm_calls"] == 0
    assert "generative_override_blocked" in result.safety.reasons or any(
        r.startswith("red_pattern:") for r in result.safety.reasons
    )


async def test_benign_utterance_stays_non_escalating() -> None:
    orchestrator = ConversationOrchestrator(llm=StubLLMProvider())
    result = await orchestrator.handle_text_turn(
        call_id="c1",
        account_id="a1",
        user_text="me siento un poco cansado pero estable",
        clinical_state=ClinicalState(),
    )
    assert result.safety.severity.value < Severity.ORANGE
    assert result.safety.escalate is False


async def test_enforce_floor_blocks_weaker_generative_default() -> None:
    """Proposed GREEN cannot downgrade a RED floor from the governor."""
    orchestrator = ConversationOrchestrator(llm=StubLLMProvider())
    result = await orchestrator.handle_text_turn(
        call_id="c1",
        account_id="a1",
        user_text="dificultad respiratoria severa",
        clinical_state=ClinicalState(),
    )
    assert result.safety.severity == Severity.RED
    assert result.safety.escalate is True
    assert result.assistant_text.startswith("Detecté señales de riesgo")
    assert "generative_override_blocked" in result.safety.reasons
    assert any(r.startswith("red_pattern:") for r in result.safety.reasons)
