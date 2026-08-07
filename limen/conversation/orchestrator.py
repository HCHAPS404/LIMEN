"""Conversation orchestrator foundation stub."""

from __future__ import annotations

from limen.conversation.session import CallSession
from limen.conversation.turn import Turn
from limen.safety.governor import SafetyGovernor


class ConversationOrchestrator:
    """Coordinates turn handling with safety floor (LLM path Planned)."""

    def __init__(self, governor: SafetyGovernor | None = None) -> None:
        self.governor = governor or SafetyGovernor()

    def handle_text_turn(self, session: CallSession, user_text: str) -> Turn:
        decision = self.governor.evaluate_utterance(user_text)
        session.latest_safety = decision
        session.turn_count += 1
        if decision.escalate:
            assistant = "Detecté señales de riesgo. Por favor contacte atención médica de urgencia."
        else:
            assistant = "Gracias. Continúe describiendo cómo se siente."
        return Turn(session_id=session.session_id, user_text=user_text, assistant_text=assistant)
