"""Knowledge forgetting — lexical + dense artifacts must be purged and verified."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from limen.knowledge.contracts import KnowledgeStatus
from limen.knowledge.vector_store import NullVectorStore, VectorStore
from limen.persistence.repositories.knowledge import SqliteKnowledgeRepository


class IncompletePurgeError(RuntimeError):
    """Raised when deletion verification finds residual active artifacts."""


class KnowledgeDeletionService:
    def __init__(
        self,
        repository: SqliteKnowledgeRepository,
        *,
        vector_store: VectorStore | None = None,
    ) -> None:
        self._repository = repository
        self._vectors = vector_store or NullVectorStore()

    def delete(self, *, account_id: str, document_id: str) -> dict[str, Any] | None:
        """Delete/forget a document from lexical and dense retrieval paths.

        Returns the final document dict (status REMOVED), or None if not found.
        Idempotent: deleting an already-REMOVED document returns that document.
        """
        existing = self._repository.get_document(account_id, document_id)
        if existing is None:
            return None
        if existing["status"] == KnowledgeStatus.REMOVED.value:
            return existing

        storage = self._repository.storage_path(account_id, document_id)
        self._repository.begin_removal(account_id, document_id)
        self._repository.purge_active_artifacts(account_id, document_id)
        self._vectors.delete_document(account_id=account_id, document_id=document_id)

        lexical_ok = self._repository.verify_forgotten(account_id, document_id)
        dense_ok = self._vectors.count_document(account_id=account_id, document_id=document_id) == 0
        if not lexical_ok or not dense_ok:
            self._repository.mark_failed(
                account_id,
                document_id,
                stage="purge",
                message=(
                    "Active retrieval artifacts remained after purge "
                    f"(lexical_ok={lexical_ok}, dense_ok={dense_ok})"
                ),
            )
            raise IncompletePurgeError(f"Purge verification failed for document_id={document_id}")

        removed = self._repository.mark_removed(account_id, document_id)
        if storage:
            path = Path(storage)
            if path.is_file():
                path.unlink(missing_ok=True)
        return removed
