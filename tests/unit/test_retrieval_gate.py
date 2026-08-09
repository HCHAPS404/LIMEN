"""Knowledge vs clinical retrieval gating."""

from __future__ import annotations

from limen.clinical.uncertainty_analysis import UncertaintyReport
from limen.conversation.retrieval_gate import (
    looks_like_knowledge_request,
    should_run_retrieval,
)


def test_protocol_and_marker_questions_look_like_knowledge() -> None:
    assert looks_like_knowledge_request(
        "¿Cuál es el marcador administrativo del protocolo ZXQ-921?"
    )
    assert looks_like_knowledge_request("Según el documento, ¿qué dice de la herida?")
    assert looks_like_knowledge_request("LUNA-73")
    assert not looks_like_knowledge_request("hola, gracias")
    assert not looks_like_knowledge_request("me duele un poco")


def test_should_run_retrieval_ors_clinical_and_knowledge() -> None:
    empty = UncertaintyReport(should_retrieve=False)
    clinical = UncertaintyReport(should_retrieve=True, unresolved=["¿fiebre?"])
    assert should_run_retrieval(empty, "hola") is False
    assert should_run_retrieval(empty, "protocolo ZXQ-921") is True
    assert should_run_retrieval(clinical, "hola") is True
