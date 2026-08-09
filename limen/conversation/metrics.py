"""Practical conversational metrics helpers (objective counts only)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from limen.conversation.continuity import is_near_duplicate


def duplicate_response_rate(responses: list[str]) -> float | None:
    if len(responses) < 2:
        return None
    dupes = 0
    for i in range(1, len(responses)):
        if is_near_duplicate(responses[i], responses[i - 1]):
            dupes += 1
    return dupes / (len(responses) - 1)


def repeated_question_rate(
    *,
    asked: list[str],
    answered_intents: set[str],
    intent_of: Callable[[str], Any],
) -> float | None:
    """Fraction of asked questions whose intent was already answered."""
    if not asked:
        return None
    bad = sum(1 for q in asked if intent_of(q) in answered_intents)
    return bad / len(asked)
