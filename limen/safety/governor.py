"""Safety Governor — deterministic, no LLM dependency."""

from __future__ import annotations

from limen.clinical.state import ClinicalState
from limen.safety.decision import SafetyDecision, Severity
from limen.safety.rules import evaluate_state_rules, evaluate_text_rules


class SafetyGovernor:
    """Monotonic safety authority that generative output cannot override downward."""

    def evaluate_utterance(self, text: str) -> SafetyDecision:
        return evaluate_text_rules(text)

    def evaluate_state(self, state: ClinicalState) -> SafetyDecision:
        """Use typed findings (present / denied / conflicting) without weakening RED."""
        return evaluate_state_rules(state)

    def merge(self, *decisions: SafetyDecision) -> SafetyDecision:
        """Severity is monotonic: the strongest decision wins."""
        if not decisions:
            return SafetyDecision.green("empty_merge")

        best = decisions[0]
        for decision in decisions[1:]:
            if decision.severity > best.severity:
                best = decision
            elif decision.severity == best.severity:
                best = SafetyDecision(
                    severity=best.severity,
                    reasons=list(dict.fromkeys([*best.reasons, *decision.reasons])),
                    escalate=best.escalate or decision.escalate,
                    policy_version=best.policy_version,
                )
        return best

    def enforce_floor(self, proposed: SafetyDecision, floor: SafetyDecision) -> SafetyDecision:
        """Generative output cannot weaken a stronger safety floor."""
        if floor.severity > proposed.severity:
            return SafetyDecision(
                severity=floor.severity,
                reasons=[*floor.reasons, "generative_override_blocked"],
                escalate=floor.escalate or floor.severity >= Severity.ORANGE,
                policy_version=floor.policy_version,
            )
        return self.merge(floor, proposed)
