"""Preferred name wiring into conversation continuity."""

from __future__ import annotations

from limen.conversation.context import ConversationContext
from limen.conversation.continuity import (
    update_context_after_assistant,
    update_context_after_patient,
)
from limen.safety.decision import SafetyDecision


def test_patient_name_captured_from_utterance() -> None:
    ctx = ConversationContext(call_id="c1")
    ctx = update_context_after_patient(ctx, user_text="hola, me llamo Juan", max_recent_turns=6)
    assert ctx.patient_display_name == "Juan"
    assert ctx.asked_preferred_name is True


def test_asked_preferred_name_from_assistant_question() -> None:
    ctx = ConversationContext(call_id="c1")
    ctx = update_context_after_patient(ctx, user_text="hola", max_recent_turns=6)
    ctx = update_context_after_assistant(
        ctx,
        assistant_text="Buenos días. ¿Cómo prefiere que le diga?",
        safety=SafetyDecision.green("generative_default"),
        open_questions=[],
        evidence_available=False,
    )
    assert ctx.asked_preferred_name is True
