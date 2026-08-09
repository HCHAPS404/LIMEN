"""In-memory knowledge registry stub for foundation."""

from __future__ import annotations

from dataclasses import dataclass, field

from limen.knowledge.contracts import KnowledgeStatus


@dataclass
class DocumentRecord:
    document_id: str
    name: str
    status: KnowledgeStatus = KnowledgeStatus.UPLOADED
    fingerprint: str = ""


@dataclass
class KnowledgeRegistry:
    documents: dict[str, DocumentRecord] = field(default_factory=dict)

    def list_available(self) -> list[DocumentRecord]:
        return [d for d in self.documents.values() if d.status == KnowledgeStatus.AVAILABLE]

    def mark_available(self, document_id: str) -> None:
        doc = self.documents[document_id]
        doc.status = KnowledgeStatus.AVAILABLE

    def mark_removed(self, document_id: str) -> None:
        doc = self.documents[document_id]
        doc.status = KnowledgeStatus.REMOVED
