"""Deterministic patient-response templates keyed by authoritative SafetyDecision.

These are the clinical-safe production fallback — not another LLM.
"""

from __future__ import annotations

from limen.clinical.state import ClinicalState
from limen.conversation.context import ConversationContext, extract_pain_severity_mention
from limen.knowledge.contracts import EvidenceChunk
from limen.safety.decision import SafetyDecision, Severity

# Keep escalation wording aligned with existing safety tests.
RED_ESCALATION_TEMPLATE = (
    "Detecté señales de riesgo. Por favor contacte atención médica de urgencia."
)
YELLOW_TEMPLATE = (
    "Hay puntos que conviene revisar con el equipo de salud. "
    "Observe cómo se siente y avise si empeora."
)
GREEN_TEMPLATE = (
    "Por ahora su descripción es compatible con una recuperación esperada. "
    "Siga las indicaciones de su equipo y avise si nota cambios."
)
# Shorter variants when greeting/boilerplate already happened.
YELLOW_CONTINUE = (
    "Queda información por precisar con el equipo de salud. "
    "Avise si nota empeoramiento."
)
GREEN_CONTINUE = (
    "Entendido. Continúe observando y avise si aparecen cambios nuevos."
)
NO_EVIDENCE_UNCERTAINTY = (
    "Todavía no tengo documentación adicional para confirmar eso; "
    "me baso en lo que ha descrito y en la decisión de seguridad actual."
)
NO_EVIDENCE_CONTINUE = (
    "Sin documentación adicional nueva, sigo con lo que ya contó."
)


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
    if safety.severity >= Severity.YELLOW:
        base = YELLOW_CONTINUE if continuing else YELLOW_TEMPLATE
    else:
        base = GREEN_CONTINUE if continuing else GREEN_TEMPLATE

    parts: list[str] = []
    # Acknowledge new concrete info when available (pain score).
    last = conversation.last_patient_utterance if conversation else None
    score = extract_pain_severity_mention(last or "")
    if score is not None:
        parts.append(f"Anoto el dolor en {score} de 10.")
    parts.append(base)

    if not evidence:
        parts.append(NO_EVIDENCE_CONTINUE if continuing else NO_EVIDENCE_UNCERTAINTY)
    elif evidence and not continuing:
        source = evidence[0].source_name
        parts.append(f"Puedo apoyarme en material ya cargado ({source}).")

    if open_questions:
        parts.append(f"Para continuar: {open_questions[0]}")

    return " ".join(parts)


# Back-compat aliases used by older imports/tests.
ESCALATION_TEMPLATE = RED_ESCALATION_TEMPLATE
FALLBACK_TEMPLATE = GREEN_TEMPLATE
EVIDENCE_TEMPLATE = (
    "Gracias. Según la documentación disponible ({source}), "
    "continúe observando los signos y avise si empeoran."
)
