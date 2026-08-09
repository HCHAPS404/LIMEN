"""Conversation continuity helpers: novelty, context update, budget trim."""

from __future__ import annotations

import re
import unicodedata
from uuid import uuid4

from limen.conversation.context import (
    ConversationContext,
    ConversationPhase,
    PendingAssistantIntent,
    PendingQuestion,
    RecentTurn,
    extract_pain_severity_mention,
    infer_question_intent,
)
from limen.safety.decision import SafetyDecision, Severity


def _norm(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text.casefold())
    folded = "".join(ch for ch in folded if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", folded).strip()


def is_near_duplicate(a: str, b: str, *, threshold: float = 0.72) -> bool:
    """Token Jaccard near-duplicate — rejects unnecessary repetition, not RED repeats."""
    ta = set(_norm(a).split())
    tb = set(_norm(b).split())
    if not ta or not tb:
        return False
    if a.strip() == b.strip():
        return True
    inter = len(ta & tb)
    union = len(ta | tb)
    return (inter / union) >= threshold if union else False


_GENERIC_OPENERS = (
    "gracias por la informacion",
    "gracias por mencionarlo",
    "entiendo",
    "para ayudarte mejor",
    "por ahora su descripcion",
)


def has_excessive_generic_opener(text: str, previous: str | None) -> bool:
    if not previous:
        return False
    n = _norm(text)
    p = _norm(previous)
    return any(n.startswith(opener) and p.startswith(opener) for opener in _GENERIC_OPENERS)


def classify_assistant_intent(
    *,
    text: str,
    safety: SafetyDecision,
    asked_question: str | None,
) -> PendingAssistantIntent:
    if safety.escalate or safety.severity >= Severity.RED:
        return PendingAssistantIntent(
            type="safety_instruction",
            safety_critical=True,
            completed=True,
            text=text,
            required_information=["seek_urgent_care"],
        )
    if asked_question:
        intent, fields = infer_question_intent(asked_question)
        return PendingAssistantIntent(
            type="question",
            safety_critical=False,
            completed=True,
            text=text,
            required_information=fields or [intent],
        )
    return PendingAssistantIntent(
        type="explanation",
        safety_critical=False,
        completed=True,
        text=text,
    )


def derive_phase(
    *,
    prior: ConversationContext,
    safety: SafetyDecision,
    open_questions: list[str],
) -> ConversationPhase:
    if safety.escalate or safety.severity >= Severity.RED:
        return ConversationPhase.ESCALATING
    if prior.turn_index <= 0:
        return ConversationPhase.OPENING
    if open_questions:
        return ConversationPhase.CLARIFYING
    if safety.severity >= Severity.YELLOW:
        return ConversationPhase.ASSESSING
    return ConversationPhase.MONITORING


def update_context_after_patient(
    ctx: ConversationContext,
    *,
    user_text: str,
    max_recent_turns: int,
) -> ConversationContext:
    """Record patient utterance and try to resolve pending question."""
    ctx = ctx.model_copy(deep=True)
    ctx.turn_index += 1
    ctx.last_patient_utterance = user_text
    ctx.recent_turns.append(
        RecentTurn(turn_index=ctx.turn_index, role="patient", text=user_text[:240])
    )
    ctx.recent_turns = ctx.recent_turns[-max_recent_turns:]

    pending = ctx.pending_question
    if pending is not None:
        answered = False
        if pending.intent == "pain_severity":
            score = extract_pain_severity_mention(user_text)
            if score is not None:
                answered = True
        elif pending.intent == "fever_status":
            if re.search(r"\b(fiebre|febril|temperatura)\b", user_text, re.I) or re.search(
                r"\bno\b.{0,24}\bfiebre\b", user_text, re.I
            ):
                answered = True
        elif pending.intent in {
            "wound_status",
            "bleeding_status",
            "breathing_status",
            "symptom_course",
        }:
            # Require topical overlap — do not close wound ask on an unrelated fever denial.
            intent_tokens = {
                "wound_status": ("herida", "cicatriz", "roja", "calor", "caliente", "supura"),
                "bleeding_status": ("sangr", "sangre"),
                "breathing_status": ("respir", "aire", "ahogo"),
                "symptom_course": ("empeor", "mejor", "igual", "desde", "ayer", "hoy"),
            }[pending.intent]
            lowered = user_text.casefold()
            if any(tok in lowered for tok in intent_tokens) and len(user_text.strip()) >= 4:
                answered = True
        elif len(user_text.strip()) >= 8:
            answered = True
        if answered:
            ctx.answered_question_ids.append(pending.id)
            if pending.intent and pending.intent not in ctx.answered_intents:
                ctx.answered_intents.append(pending.intent)
            ctx.pending_question = None
    return ctx


def update_context_after_assistant(
    ctx: ConversationContext,
    *,
    assistant_text: str,
    safety: SafetyDecision,
    open_questions: list[str],
    evidence_available: bool,
    interrupted: bool = False,
    max_recent_turns: int = 6,
) -> ConversationContext:
    ctx = ctx.model_copy(deep=True)
    ctx.previous_assistant_response = assistant_text
    ctx.previous_response_interrupted = interrupted
    ctx.evidence_available = evidence_available
    ctx.current_safety = safety
    ctx.greeting_done = True
    ctx.phase = derive_phase(prior=ctx, safety=safety, open_questions=open_questions)
    ctx.recent_turns.append(
        RecentTurn(
            turn_index=ctx.turn_index,
            role="assistant",
            text=assistant_text[:240],
            interrupted=interrupted,
        )
    )
    ctx.recent_turns = ctx.recent_turns[-max_recent_turns:]

    asked: str | None = None
    if open_questions and not (safety.escalate or safety.severity >= Severity.RED):
        asked = open_questions[0]
        # Avoid re-asking already answered question ids by text match.
        q_intent, fields = infer_question_intent(asked)
        qid = uuid4().hex[:12]
        ctx.pending_question = PendingQuestion(
            id=qid,
            intent=q_intent,
            requested_fields=fields,
            text=asked,
            asked_at_turn=ctx.turn_index,
        )
    elif safety.escalate or safety.severity >= Severity.RED:
        ctx.pending_question = None

    pending_intent = classify_assistant_intent(
        text=assistant_text, safety=safety, asked_question=asked
    )
    pending_intent.interrupted = interrupted
    pending_intent.completed = not interrupted
    ctx.pending_assistant_intent = pending_intent
    return ctx


def mark_interrupted(ctx: ConversationContext) -> ConversationContext:
    ctx = ctx.model_copy(deep=True)
    ctx.previous_response_interrupted = True
    if ctx.pending_assistant_intent is not None:
        ctx.pending_assistant_intent = ctx.pending_assistant_intent.model_copy(
            update={"interrupted": True, "completed": False}
        )
    if ctx.recent_turns and ctx.recent_turns[-1].role == "assistant":
        ctx.recent_turns[-1] = ctx.recent_turns[-1].model_copy(update={"interrupted": True})
    return ctx


def filter_open_questions(
    open_questions: list[str],
    ctx: ConversationContext,
) -> list[str]:
    """Drop questions that match already-answered intents."""
    answered_intents = set(ctx.answered_intents)
    for turn in ctx.recent_turns:
        if turn.role == "patient" and extract_pain_severity_mention(turn.text) is not None:
            answered_intents.add("pain_severity")
    last_patient = ctx.last_patient_utterance or ""
    if extract_pain_severity_mention(last_patient) is not None:
        answered_intents.add("pain_severity")
    out: list[str] = []
    for question in open_questions:
        intent, _fields = infer_question_intent(question)
        if intent in answered_intents:
            continue
        out.append(question)
    return out
