"""Document lifecycle state transitions — explicit, no optimistic AVAILABLE."""

from __future__ import annotations

from limen.knowledge.contracts import KnowledgeStatus

# Allowed directed edges for document status.
_TRANSITIONS: dict[KnowledgeStatus, frozenset[KnowledgeStatus]] = {
    KnowledgeStatus.UPLOADED: frozenset(
        {KnowledgeStatus.PROCESSING, KnowledgeStatus.FAILED, KnowledgeStatus.REMOVING}
    ),
    KnowledgeStatus.PROCESSING: frozenset(
        {KnowledgeStatus.AVAILABLE, KnowledgeStatus.FAILED, KnowledgeStatus.REMOVING}
    ),
    KnowledgeStatus.AVAILABLE: frozenset({KnowledgeStatus.REMOVING, KnowledgeStatus.FAILED}),
    KnowledgeStatus.FAILED: frozenset({KnowledgeStatus.REMOVING, KnowledgeStatus.PROCESSING}),
    KnowledgeStatus.REMOVING: frozenset({KnowledgeStatus.REMOVED, KnowledgeStatus.FAILED}),
    KnowledgeStatus.REMOVED: frozenset(),
}


class InvalidStatusTransition(ValueError):
    pass


def can_transition(current: KnowledgeStatus, target: KnowledgeStatus) -> bool:
    if current == target:
        return True
    return target in _TRANSITIONS.get(current, frozenset())


def assert_transition(current: KnowledgeStatus, target: KnowledgeStatus) -> None:
    if not can_transition(current, target):
        raise InvalidStatusTransition(f"Cannot transition {current.value} → {target.value}")
