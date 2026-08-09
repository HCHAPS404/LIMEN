"""Deterministic patient-response templates keyed by authoritative SafetyDecision.

These are the clinical-safe production fallback — not another LLM.
"""

from __future__ import annotations

from limen.clinical.state import ClinicalState
from limen.conversation.context import ConversationContext, extract_pain_severity_mention
from limen.conversation.session_intent import looks_like_greeting_only, opening_reply
from limen.knowledge.contracts import EvidenceChunk
from limen.safety.decision import SafetyDecision, Severity

# Keep escalation wording aligned with existing safety tests.
RED_ESCALATION_TEMPLATE = (
    "Detecté señales de riesgo. Por favor contacte atención médica de urgencia."
)
YELLOW_TEMPLATE = (
    "Hay puntos que conviene revisar con su equipo de salud. "
    "Observe cómo se siente y avise si empeora."
)
GREEN_TEMPLATE = (
    "Por ahora lo que describe es compatible con una recuperación esperada. "
    "Siga las indicaciones de su equipo y avise si nota cambios."
)
# Shorter variants when greeting/boilerplate already happened.
YELLOW_CONTINUE = (
    "Queda información por precisar con su equipo de salud. "
    "Avise si nota empeoramiento."
)
GREEN_CONTINUE = (
    "De acuerdo. Continúe observando y avise si aparecen cambios nuevos."
)
NO_EVIDENCE_UNCERTAINTY = (
    "Todavía no tengo documentación adicional para confirmar eso; "
    "me baso en lo que usted ha descrito y en la decisión de seguridad actual."
)
NO_EVIDENCE_CONTINUE = (
    "Sin documentación adicional nueva, sigo con lo que usted ya contó."
)


def _vocative_prefix(conversation: ConversationContext | None) -> str:
    name = conversation.patient_display_name if conversation else None
    if not name:
        return ""
    # Presentation-only; default clinical vocative without inventing gender beyond señor.
    return f"Señor {name}, "


def deterministic_patient_reply(
    *,
    safety: SafetyDecision,
    clinical_state: ClinicalState | None = None,
    evidence: list[EvidenceChunk] | None = None,
    open_questions: list[str] | None = None,
    conversation: ConversationContext | None = None,
) -> str:
    """Build a patient-facing reply from authoritative state only."""
    evidence = evidence or []
    open_questions = open_questions or []
    if clinical_state is not None and not open_questions:
        open_questions = list(clinical_state.open_questions)

    if safety.escalate or safety.severity >= Severity.RED:
        # If RED was interrupted, still deliver the critical next step.
        if (
            conversation
            and conversation.pending_assistant_intent
            and conversation.pending_assistant_intent.safety_critical
            and conversation.pending_assistant_intent.interrupted
        ):
            return (
                "Sigo detectando señales de riesgo: busque atención médica "
                "de urgencia ahora."
            )
        return RED_ESCALATION_TEMPLATE

    continuing = bool(conversation and conversation.greeting_done)
    last = conversation.last_patient_utterance if conversation else None

    # First-turn greetings must not sound like a clinical status report.
    if (
        not continuing
        and looks_like_greeting_only(last or "")
        and not (safety.escalate or safety.severity >= Severity.RED)
    ):
        return opening_reply(
            assistant_name=(
                conversation.assistant_display_name if conversation else None
            ),
            gender=conversation.assistant_gender if conversation else None,
            display_name=(
                conversation.patient_display_name if conversation else None
            ),
            user_text=last or "",
        )

    if safety.severity >= Severity.YELLOW:
        base = YELLOW_CONTINUE if continuing else YELLOW_TEMPLATE
    else:
        base = GREEN_CONTINUE if continuing else GREEN_TEMPLATE

    parts: list[str] = []
    vocative = _vocative_prefix(conversation)
    # Acknowledge new concrete info when available (pain score).
    score = extract_pain_severity_mention(last or "")
    if score is not None:
        parts.append(f"{vocative}Anoto su dolor en {score} de 10.")
        vocative = ""
    elif vocative and not continuing:
        parts.append(f"{vocative}gracias por comunicarse.")
        vocative = ""
    parts.append(base if not vocative else f"{vocative}{base[0].lower()}{base[1:]}")

    # Skip "no documentation" hedging on empty openings / pure acks.
    if not evidence and not looks_like_greeting_only(last or ""):
        parts.append(NO_EVIDENCE_CONTINUE if continuing else NO_EVIDENCE_UNCERTAINTY)
    elif evidence and not continuing:
        source = evidence[0].source_name
        parts.append(f"Puedo apoyarme en material ya cargado ({source}).")

    if open_questions and not looks_like_greeting_only(last or ""):
        parts.append(f"Para continuar: {open_questions[0]}")

    return " ".join(parts)


# Back-compat aliases used by older imports/tests.
ESCALATION_TEMPLATE = RED_ESCALATION_TEMPLATE
FALLBACK_TEMPLATE = GREEN_TEMPLATE
EVIDENCE_TEMPLATE = (
    "Según la documentación disponible ({source}): {snippet} "
    "¿Quiere que lo detalle un poco más?"
)


def evidence_grounded_reply(evidence: list[EvidenceChunk]) -> str:
    """Short spoken answer that surfaces retrieved fact text (no invention)."""
    chunk = evidence[0]
    source = chunk.source_name or "documento cargado"
    # Prefer a compact excerpt; strip markdown noise for TTS.
    raw = (chunk.text or "").replace("**", "").replace("#", " ").strip()
    snippet = " ".join(raw.split())
    if len(snippet) > 220:
        snippet = snippet[:217].rstrip() + "…"
    return EVIDENCE_TEMPLATE.format(source=source, snippet=snippet)
