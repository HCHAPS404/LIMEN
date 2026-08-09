"""Decide when hybrid retrieval should run for a patient turn.

Clinical uncertainty still owns ``UncertaintyReport.should_retrieve``.
Knowledge-seeking utterances (protocol / document / admin markers) must also
retrieve so live knowledge (G5) answers without inventing clinical findings.
"""

from __future__ import annotations

import re

from limen.clinical.uncertainty_analysis import UncertaintyReport

# Substrings that strongly suggest the patient is asking about loaded docs.
_KNOWLEDGE_HINTS: tuple[str, ...] = (
    "protocolo",
    "documento",
    "documentación",
    "documentacion",
    "manual",
    "guía",
    "guia",
    "marcador",
    "según el",
    "segun el",
    "qué dice",
    "que dice",
    "información sobre",
    "informacion sobre",
    "base de conocimiento",
    "instructivo",
    "política",
    "politica",
    "norma escrita",
    "procedimiento escrito",
)

# Alphanumeric admin/protocol codes like ZXQ-921 or LUNA-73.
_CODE_RE = re.compile(r"\b[a-z]{2,6}[-_]?\d{2,5}\b", re.IGNORECASE)


def looks_like_knowledge_request(text: str) -> bool:
    """True when the utterance likely needs document evidence, not only clinical RAG."""
    raw = (text or "").strip()
    if not raw:
        return False
    folded = raw.casefold()
    if any(hint in folded for hint in _KNOWLEDGE_HINTS):
        return True
    return _CODE_RE.search(raw) is not None


def should_run_retrieval(report: UncertaintyReport, user_text: str) -> bool:
    """Clinical uncertainty OR knowledge-seeking patient text."""
    return bool(report.should_retrieve) or looks_like_knowledge_request(user_text)
