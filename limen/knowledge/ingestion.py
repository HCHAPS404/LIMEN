"""Hot knowledge ingestion — accept quickly, process asynchronously."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from limen.config.settings import ApplicationSettings
from limen.knowledge.contracts import EmbeddingProvider, EvidenceChunk, KnowledgeStatus
from limen.knowledge.embeddings import build_embedding_provider
from limen.knowledge.ocr import OCRUnavailableError
from limen.knowledge.parsing import assert_supported_filename, parse_document
from limen.knowledge.vector_store import NullVectorStore, VectorStore, get_vector_store
from limen.persistence.repositories.knowledge import (
    SqliteKnowledgeRepository,
    sha256_bytes,
)
from limen.telemetry.logging import get_telemetry_logger, log_event

_log = get_telemetry_logger("limen.knowledge")

# Linux NAME_MAX is 255 bytes; original PDF titles in the official corpus can exceed that
# when prefixed with document_id. Keep the on-disk basename short; source_name stays human.
_MAX_STORAGE_BASENAME = 180


def storage_basename(document_id: str, source_name: str) -> str:
    """Stable short on-disk name. Provenance uses source_name, not this basename."""
    suffix = Path(source_name).suffix.lower()
    if not suffix or len(suffix.encode("utf-8")) > 16:
        suffix = ".bin"
    name = f"{document_id}{suffix}"
    encoded = name.encode("utf-8")
    if len(encoded) > _MAX_STORAGE_BASENAME:
        name = f"{document_id}.bin"
    return name


class DuplicateDocumentError(ValueError):
    def __init__(self, existing: dict[str, Any]) -> None:
        self.existing = existing
        super().__init__(
            f"Duplicate content already active as document_id={existing['document_id']}"
        )


class KnowledgeIngestionService:
    def __init__(
        self,
        repository: SqliteKnowledgeRepository,
        settings: ApplicationSettings,
        *,
        embeddings: EmbeddingProvider | None = None,
        vector_store: VectorStore | None = None,
    ) -> None:
        self._repository = repository
        self._settings = settings
        self._embeddings = embeddings or build_embedding_provider(settings)
        self._vectors = vector_store or get_vector_store(
            settings, dimensions=self._embeddings.dimensions
        )

    def accept_upload(
        self,
        *,
        account_id: str,
        filename: str,
        payload: bytes,
    ) -> dict[str, Any]:
        """Validate, persist, mark PROCESSING, and return without indexing."""
        if not payload:
            raise ValueError("Uploaded file is empty")

        max_bytes = self._settings.max_upload_mb * 1024 * 1024
        if len(payload) > max_bytes:
            raise ValueError(f"Document exceeds MAX_UPLOAD_MB={self._settings.max_upload_mb}")

        safe_name = Path(filename).name or "document.bin"
        assert_supported_filename(safe_name)

        digest = sha256_bytes(payload)
        duplicate = self._repository.find_active_by_sha256(account_id, digest)
        if duplicate is not None:
            raise DuplicateDocumentError(duplicate)

        storage_dir = self._settings.document_path / account_id
        storage_dir.mkdir(parents=True, exist_ok=True)
        document = self._repository.create_document(
            account_id=account_id,
            source_name=safe_name,
            size_bytes=len(payload),
            storage_path="",
            sha256=digest,
        )
        document_id = document["document_id"]
        target = storage_dir / storage_basename(document_id, safe_name)
        target.write_bytes(payload)
        self._repository.set_storage_path(account_id, document_id, str(target))
        processing = self._repository.mark_processing(account_id, document_id)
        return processing or document

    def process_document(self, *, account_id: str, document_id: str) -> dict[str, Any] | None:
        """Parse → chunk → lexical + dense index → verify both → AVAILABLE."""
        document = self._repository.get_document(account_id, document_id)
        if document is None:
            return None
        if document["status"] != KnowledgeStatus.PROCESSING.value:
            self._repository.append_event(
                account_id=account_id,
                document_id=document_id,
                stage="knowledge.processing_aborted",
                label="Processing aborted",
                detail=f"status={document['status']}",
            )
            return document

        storage = self._repository.storage_path(account_id, document_id)
        if not storage:
            self._fail_if_processing(
                account_id, document_id, stage="ingest", message="Missing storage path"
            )
            return self._repository.get_document(account_id, document_id)

        path = Path(storage)
        safe_name = document["source_name"]
        version_id = document.get("active_version_id")
        dense_written = False

        try:
            if not self._ensure_processing(account_id, document_id):
                return self._repository.get_document(account_id, document_id)

            t_parse = time.perf_counter()
            parsed = parse_document(path, filename=safe_name)
            parse_ms = (time.perf_counter() - t_parse) * 1000.0
            self._repository.append_event(
                account_id=account_id,
                document_id=document_id,
                stage="knowledge.parsed",
                label="Document parsed",
                detail=parsed.parser,
                duration_ms=parse_ms,
                payload={"ocr_applied": parsed.ocr_applied, "pages": len(parsed.pages)},
            )
            if parsed.ocr_applied:
                self._repository.append_event(
                    account_id=account_id,
                    document_id=document_id,
                    stage="knowledge.ocr.completed",
                    event_type="knowledge.ocr.completed",
                    label="OCR completed",
                    detail=parsed.parser,
                    payload={"pages": len(parsed.pages)},
                )
            pages = [(page.page, page.text) for page in parsed.pages if page.text.strip()]
            if not pages:
                raise ValueError("Document contained no text")
            if not version_id:
                raise RuntimeError("Document missing active_version_id")

            if not self._ensure_processing(account_id, document_id):
                return self._repository.get_document(account_id, document_id)

            t_chunk = time.perf_counter()
            chunks = self._repository.build_chunks_for_pages(
                document_id=document_id,
                version_id=version_id,
                filename=safe_name,
                pages=pages,
            )
            chunk_ms = (time.perf_counter() - t_chunk) * 1000.0
            if not chunks:
                raise ValueError("Chunking produced no chunks")

            if not self._ensure_processing(account_id, document_id):
                return self._repository.get_document(account_id, document_id)

            page_count = len({p for p, _ in pages if p is not None}) or None
            t_lex = time.perf_counter()
            self._repository.index_chunks(
                account_id=account_id,
                document_id=document_id,
                version_id=version_id,
                source_name=safe_name,
                chunks=chunks,
                parser=parsed.parser,
                ocr_applied=parsed.ocr_applied,
                page_count=page_count,
            )
            lexical_ms = (time.perf_counter() - t_lex) * 1000.0

            if not self._ensure_processing(account_id, document_id):
                self._compensate(account_id, document_id)
                self._repository.append_event(
                    account_id=account_id,
                    document_id=document_id,
                    stage="knowledge.processing_aborted",
                    label="Skipped AVAILABLE after status change",
                    detail="purged compensating index artifacts",
                )
                return self._repository.get_document(account_id, document_id)

            probe = chunks[0].text.split()[0] if chunks[0].text.split() else None
            t_verify = time.perf_counter()
            if not self._repository.verify_indexed(
                account_id=account_id,
                document_id=document_id,
                version_id=version_id,
                probe_token=probe,
            ):
                raise RuntimeError("Index verification failed: chunk/FTS mismatch")
            verify_ms = (time.perf_counter() - t_verify) * 1000.0

            evidence_chunks = [
                EvidenceChunk(
                    document_id=chunk.document_id,
                    chunk_id=chunk.chunk_id,
                    text=chunk.text,
                    source_name=chunk.filename,
                    filename=chunk.filename,
                    page=chunk.page,
                    section=chunk.section,
                    version=1,
                    version_id=chunk.version_id,
                    content_hash=chunk.content_hash,
                    active=True,
                    retrieval_modes=["dense"],
                )
                for chunk in chunks
            ]
            t_embed = time.perf_counter()
            vectors = self._embeddings.embed_documents([c.text for c in evidence_chunks])
            embed_ms = (time.perf_counter() - t_embed) * 1000.0
            t_dense = time.perf_counter()
            self._vectors.upsert_chunks(
                account_id=account_id,
                chunks=evidence_chunks,
                vectors=vectors,
            )
            dense_ms = (time.perf_counter() - t_dense) * 1000.0
            dense_written = True
            self._repository.append_event(
                account_id=account_id,
                document_id=document_id,
                stage="knowledge.dense_indexed",
                label="Dense vectors indexed",
                detail=f"chunks={len(evidence_chunks)}",
                duration_ms=dense_ms,
                payload={
                    "vector_count": len(evidence_chunks),
                    "chunk_ms": chunk_ms,
                    "lexical_ms": lexical_ms,
                    "embed_ms": embed_ms,
                    "dense_ms": dense_ms,
                    "verify_ms": verify_ms,
                },
            )

            needs_dense_verify = not isinstance(self._vectors, NullVectorStore)
            dense_ok = not needs_dense_verify or self._vectors.verify_document_indexed(
                account_id=account_id,
                document_id=document_id,
                expected_chunks=len(evidence_chunks),
            )
            if not dense_ok:
                raise RuntimeError("Dense index verification failed: vector count mismatch")

            if not self._ensure_processing(account_id, document_id):
                self._compensate(account_id, document_id)
                return self._repository.get_document(account_id, document_id)

            available = self._repository.mark_available(account_id, document_id)
            log_event(
                _log,
                "knowledge.available",
                document_id=document_id,
                duration_ms=parse_ms + chunk_ms + lexical_ms + embed_ms + dense_ms,
            )
            return available
        except OCRUnavailableError as error:
            if dense_written:
                self._compensate(account_id, document_id)
            self._fail_if_processing(account_id, document_id, stage="ocr", message=str(error))
            return self._repository.get_document(account_id, document_id)
        except Exception as error:  # noqa: BLE001 — surface as FAILED when still processing
            if dense_written:
                self._compensate(account_id, document_id)
            else:
                # Lexical artifacts may already exist — purge so FAILED is not half-indexed.
                self._repository.purge_active_artifacts(account_id, document_id)
            stage = "ingest"
            message = str(error)
            if "parse" in message.lower() or "PDF" in message or "pymupdf" in message.lower():
                stage = "parse"
            elif "Chunking" in message or "chunk" in message.lower():
                stage = "chunk"
            elif "Dense index" in message or "vector" in message.lower():
                stage = "dense_index"
            elif "Index verification" in message or "FTS" in message:
                stage = "verify"
            elif "index" in message.lower():
                stage = "index"
            self._fail_if_processing(account_id, document_id, stage=stage, message=message)
            return self._repository.get_document(account_id, document_id)

    def ingest_upload(
        self,
        *,
        account_id: str,
        filename: str,
        payload: bytes,
    ) -> dict[str, Any]:
        """Backward-compatible sync path: accept then process inline."""
        accepted = self.accept_upload(account_id=account_id, filename=filename, payload=payload)
        processed = self.process_document(
            account_id=account_id, document_id=accepted["document_id"]
        )
        return processed or accepted

    def fail_interrupted_processing(self) -> int:
        """Startup policy: PROCESSING leftovers → FAILED(interrupted_processing)."""
        return self._repository.fail_all_processing(
            stage="interrupted_processing",
            message="Application restarted while document was still PROCESSING",
        )

    def _compensate(self, account_id: str, document_id: str) -> None:
        self._repository.purge_active_artifacts(account_id, document_id)
        self._vectors.delete_document(account_id=account_id, document_id=document_id)

    def _ensure_processing(self, account_id: str, document_id: str) -> bool:
        doc = self._repository.get_document(account_id, document_id)
        return bool(doc and doc["status"] == KnowledgeStatus.PROCESSING.value)

    def _fail_if_processing(
        self,
        account_id: str,
        document_id: str,
        *,
        stage: str,
        message: str,
    ) -> None:
        if self._ensure_processing(account_id, document_id):
            self._repository.mark_failed(account_id, document_id, stage=stage, message=message)
