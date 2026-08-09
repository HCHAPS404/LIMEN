"""Typed conversation continuity state — not a raw chat log dump."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field

from limen.safety.decision import SafetyDecision


class ConversationPhase(StrEnum):
    OPENING = "OPENING"
    ASSESSING = "ASSESSING"
    CLARIFYING = "CLARIFYING"
    ESCALATING = "ESCALATING"
    MONITORING = "MONITORING"
    CLOSING = "CLOSING"


class PendingQuestion(BaseModel):
    id: str
    intent: str
    requested_fields: list[str] = Field(default_factory=list)
    text: str = ""
    asked_at_turn: int = 0


class PendingAssistantIntent(BaseModel):
    type: Literal[
        "question",
        "explanation",
        "safety_instruction",
        "ack",
        "other",
    ] = "other"
    safety_critical: bool = False
    completed: bool = False
    interrupted: bool = False
    text: str = ""
    required_information: list[str] = Field(default_factory=list)


class RecentTurn(BaseModel):
    turn_index: int
    role: Literal["patient", "assistant"]
    text: str
    interrupted: bool = False


class ConversationContext(BaseModel):
    """Bounded structured memory for multi-turn voice/text continuity."""

    call_id: str = ""
    turn_index: int = 0
    phase: ConversationPhase = ConversationPhase.OPENING
    pending_question: PendingQuestion | None = None
    answered_question_ids: list[str] = Field(default_factory=list)
    answered_intents: list[str] = Field(default_factory=list)
    pending_assistant_intent: PendingAssistantIntent | None = None
    recent_turns: list[RecentTurn] = Field(default_factory=list)
    previous_assistant_response: str | None = None
    previous_response_interrupted: bool = False
    last_patient_utterance: str | None = None
    evidence_available: bool = False
    current_safety: SafetyDecision | None = None
    greeting_done: bool = False
    patient_display_name: str | None = None
    asked_preferred_name: bool = False
    # Assistant voice persona for this call only (settings → createCall).
    assistant_persona_id: str | None = None
    assistant_display_name: str | None = None
    assistant_gender: Literal["female", "male"] | None = None

    def debug_view(self) -> dict[str, Any]:
        """Safe structured snapshot for debug UI / TRAZA (no chain-of-thought)."""
        return {
            "turn_index": self.turn_index,
            "phase": self.phase.value,
            "pending_question": (
                self.pending_question.model_dump(mode="json") if self.pending_question else None
            ),
            "answered_question_ids": list(self.answered_question_ids),
            "answered_intents": list(self.answered_intents),
            "pending_assistant_intent": (
                self.pending_assistant_intent.model_dump(mode="json")
                if self.pending_assistant_intent
                else None
            ),
            "recent_turn_ids": [f"{t.role}:{t.turn_index}" for t in self.recent_turns],
            "previous_response_interrupted": self.previous_response_interrupted,
            "evidence_available": self.evidence_available,
            "greeting_done": self.greeting_done,
            "patient_display_name": self.patient_display_name,
            "asked_preferred_name": self.asked_preferred_name,
            "assistant_persona_id": self.assistant_persona_id,
            "assistant_display_name": self.assistant_display_name,
            "assistant_gender": self.assistant_gender,
            "current_severity": (
                self.current_safety.severity.name if self.current_safety else None
            ),
        }


def infer_question_intent(question: str) -> tuple[str, list[str]]:
    """Map follow-up question text to a coarse intent (not clinical authority)."""
    q = question.casefold()
    # Intensity before course so "evolución + intensidad" counts as severity ask.
    if any(
        tok in q for tok in ("intens", "escala", "0 a 10", "0-10", "cuánto duele", "cuanto duele")
    ):
        return "pain_severity", ["pain_severity"]
    if any(tok in q for tok in ("empeor", "mejor", "evoluci", "sigue igual", "desde cu")):
        return "symptom_course", ["course"]
    if any(tok in q for tok in ("fiebre", "temperatura")):
        return "fever_status", ["fever"]
    if any(tok in q for tok in ("herida", "roja", "enrojec", "caliente", "supura")):
        return "wound_status", ["wound"]
    if any(tok in q for tok in ("respir", "aire", "ahogo")):
        return "breathing_status", ["breathing"]
    if any(tok in q for tok in ("sangrad", "sangre")):
        return "bleeding_status", ["bleeding"]
    if "dolor" in q or "duele" in q:
        return "pain_severity", ["pain_severity"]
    return "clarification", []


def extract_pain_severity_mention(text: str) -> int | None:
    """Parse informal Spanish severity like 'un siete' / '7/10'.

    When the patient reports a transition («bajó de 7 a 4»), returns the
    **current** value (4). Peak is recovered via ``extract_pain_severity_transition``.
    """
    transition = extract_pain_severity_transition(text)
    if transition is not None:
        _peak, current = transition
        return current
    return _parse_single_severity_token(text)


def extract_pain_severity_transition(text: str) -> tuple[int, int] | None:
    """Return (peak, current) for phrases like 'de 7 a 4' / 'bajó a un cuatro'."""
    import re

    folded = text.casefold()
    m = re.search(
        r"\b(?:de|desde)\s+"
        r"(diez|nueve|ocho|siete|seis|cinco|cuatro|tres|dos|uno|10|[0-9])"
        r"\s+a\s+"
        r"(diez|nueve|ocho|siete|seis|cinco|cuatro|tres|dos|uno|10|[0-9])\b",
        folded,
    )
    if m:
        peak = _severity_token_to_int(m.group(1))
        current = _severity_token_to_int(m.group(2))
        if peak is not None and current is not None:
            return peak, current
    return None


def _severity_token_to_int(raw: str) -> int | None:
    words = {
        "uno": 1,
        "dos": 2,
        "tres": 3,
        "cuatro": 4,
        "cinco": 5,
        "seis": 6,
        "siete": 7,
        "ocho": 8,
        "nueve": 9,
        "diez": 10,
    }
    if raw in words:
        return words[raw]
    try:
        value = int(raw)
    except ValueError:
        return None
    if 0 <= value <= 10:
        return value
    return None


def _parse_single_severity_token(text: str) -> int | None:
    import re

    m = re.search(
        r"\b(?:un[ao]?\s+)?(diez|nueve|ocho|siete|seis|cinco|cuatro|tres|dos|uno|0?\d|10)\b"
        r"(?:\s*(?:/|sobre)\s*10)?",
        text.casefold(),
    )
    if not m:
        return None
    return _severity_token_to_int(m.group(1))
