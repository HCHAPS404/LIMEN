"""Local Qdrant vector store — embedded path mode, no Docker/cloud server."""

from __future__ import annotations

import json
import re
import threading
from pathlib import Path
from typing import Any, Protocol

from limen.config.settings import ApplicationSettings
from limen.knowledge.contracts import EvidenceChunk
from limen.knowledge.embeddings import build_embedding_provider, embedding_fingerprint


class VectorStore(Protocol):
    def upsert_chunks(
        self,
        *,
        account_id: str,
        chunks: list[EvidenceChunk],
        vectors: list[list[float]],
    ) -> None: ...

    def search(
        self,
        *,
        account_id: str,
        vector: list[float],
        limit: int = 5,
    ) -> list[EvidenceChunk]: ...

    def delete_document(self, *, account_id: str, document_id: str) -> None: ...

    def count_document(self, *, account_id: str, document_id: str) -> int: ...

    def verify_document_indexed(
        self, *, account_id: str, document_id: str, expected_chunks: int
    ) -> bool: ...


_META_NAME = "embedding_index.json"


class QdrantVectorStore:
    """Persistent local Qdrant collection with provenance payloads.

    Collection identity includes embedding fingerprint (provider|model|dim|metric).
    Incompatible indexes are dropped and recreated — callers must re-ingest.
    """

    def __init__(
        self,
        path: Path,
        *,
        dimensions: int,
        fingerprint: str,
    ) -> None:
        from qdrant_client import QdrantClient
        from qdrant_client.http import models as qm

        self._path = path
        self._path.mkdir(parents=True, exist_ok=True)
        self._dimensions = dimensions
        self._fingerprint = fingerprint
        self._qm = qm
        self.COLLECTION = _collection_name(fingerprint)
        self._client = QdrantClient(path=str(self._path))
        self._ensure_compatible_collection()

    @property
    def dimensions(self) -> int:
        return self._dimensions

    @property
    def fingerprint(self) -> str:
        return self._fingerprint

    def close(self) -> None:
        close = getattr(self._client, "close", None)
        if callable(close):
            close()

    def _meta_path(self) -> Path:
        return self._path / _META_NAME

    def _read_meta(self) -> dict[str, Any] | None:
        path = self._meta_path()
        if not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def _write_meta(self, *, reindex_required: bool = False) -> None:
        payload = {
            "fingerprint": self._fingerprint,
            "dimensions": self._dimensions,
            "distance": "Cosine",
            "collection": self.COLLECTION,
            "reindex_required": reindex_required,
        }
        self._meta_path().write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def _ensure_compatible_collection(self) -> None:
        qm = self._qm
        meta = self._read_meta()
        names = {c.name for c in self._client.get_collections().collections}
        recreate = False
        reason = ""

        if meta is not None and meta.get("fingerprint") != self._fingerprint:
            recreate = True
            reason = (
                f"fingerprint mismatch: stored={meta.get('fingerprint')!r} "
                f"requested={self._fingerprint!r}"
            )
        elif self.COLLECTION in names:
            info = self._client.get_collection(self.COLLECTION)
            vectors = info.config.params.vectors
            size = getattr(vectors, "size", None)
            if size is None and isinstance(vectors, dict):
                # Named vectors — not used; treat as incompatible.
                size = None
            if size is not None and int(size) != self._dimensions:
                recreate = True
                reason = f"dimension mismatch: stored={size} requested={self._dimensions}"
        elif meta is not None and meta.get("collection") in names:
            # Fingerprint changed collection name — drop stale named collections later.
            recreate = True
            reason = "collection name changed with embedding fingerprint"

        if recreate:
            for name in list(names):
                if name.startswith("limen_"):
                    self._client.delete_collection(name)
            names = {c.name for c in self._client.get_collections().collections}
            self._write_meta(reindex_required=True)
            # Stale vectors are gone; knowledge corpus must be re-ingested.
            _ = reason  # retained for debuggers / future structured logs

        if self.COLLECTION not in names:
            self._client.create_collection(
                collection_name=self.COLLECTION,
                vectors_config=qm.VectorParams(
                    size=self._dimensions,
                    distance=qm.Distance.COSINE,
                ),
            )
            self._write_meta(reindex_required=recreate)

    def upsert(
        self,
        *,
        account_id: str,
        document_id: str,
        version_id: str,
        chunk_id: str,
        vector: list[float],
        text: str,
        filename: str,
        page: int | None,
        section: str | None,
        version: int = 1,
        content_hash: str | None = None,
        active: bool = True,
    ) -> None:
        qm = self._qm
        if len(vector) != self._dimensions:
            raise ValueError(
                f"vector dim {len(vector)} != collection dim {self._dimensions}"
            )
        payload: dict[str, Any] = {
            "account_id": account_id,
            "document_id": document_id,
            "version_id": version_id,
            "chunk_id": chunk_id,
            "filename": filename,
            "source_name": filename,
            "page": page,
            "section": section,
            "version": version,
            "content_hash": content_hash,
            "active": active,
            "text": text,
            "embedding_fingerprint": self._fingerprint,
        }
        self._client.upsert(
            collection_name=self.COLLECTION,
            points=[
                qm.PointStruct(
                    id=_point_id(chunk_id),
                    vector=vector,
                    payload=payload,
                )
            ],
        )

    def upsert_chunks(
        self,
        *,
        account_id: str,
        chunks: list[EvidenceChunk],
        vectors: list[list[float]],
    ) -> None:
        if len(chunks) != len(vectors):
            raise ValueError("chunks/vectors length mismatch")
        for chunk, vector in zip(chunks, vectors, strict=True):
            self.upsert(
                account_id=account_id,
                document_id=chunk.document_id,
                version_id=chunk.version_id or "",
                chunk_id=chunk.chunk_id,
                vector=vector,
                text=chunk.text,
                filename=chunk.filename or chunk.source_name,
                page=chunk.page,
                section=chunk.section,
                version=chunk.version,
                content_hash=chunk.content_hash,
                active=chunk.active,
            )

    def search(
        self,
        *,
        account_id: str,
        vector: list[float],
        limit: int = 5,
    ) -> list[EvidenceChunk]:
        qm = self._qm
        response = self._client.query_points(
            collection_name=self.COLLECTION,
            query=vector,
            limit=limit,
            query_filter=qm.Filter(
                must=[
                    qm.FieldCondition(
                        key="account_id",
                        match=qm.MatchValue(value=account_id),
                    ),
                    qm.FieldCondition(
                        key="active",
                        match=qm.MatchValue(value=True),
                    ),
                ]
            ),
        )
        evidence: list[EvidenceChunk] = []
        for point in response.points:
            payload = point.payload or {}
            if not payload.get("active", True):
                continue
            # Refuse stale points tagged with a different embedding fingerprint.
            point_fp = payload.get("embedding_fingerprint")
            if point_fp is not None and point_fp != self._fingerprint:
                continue
            evidence.append(
                EvidenceChunk(
                    document_id=str(payload.get("document_id", "")),
                    chunk_id=str(payload.get("chunk_id", "")),
                    text=str(payload.get("text", "")),
                    source_name=str(
                        payload.get("source_name") or payload.get("filename") or ""
                    ),
                    filename=str(
                        payload.get("filename") or payload.get("source_name") or ""
                    ),
                    page=payload.get("page"),
                    section=payload.get("section"),
                    score=float(point.score or 0.0),
                    version=int(payload.get("version") or 1),
                    version_id=payload.get("version_id"),
                    content_hash=payload.get("content_hash"),
                    active=bool(payload.get("active", True)),
                    retrieval_modes=["dense"],
                )
            )
        return evidence

    def delete_document(self, *, account_id: str, document_id: str) -> None:
        qm = self._qm
        self._client.delete(
            collection_name=self.COLLECTION,
            points_selector=qm.FilterSelector(
                filter=qm.Filter(
                    must=[
                        qm.FieldCondition(
                            key="account_id",
                            match=qm.MatchValue(value=account_id),
                        ),
                        qm.FieldCondition(
                            key="document_id",
                            match=qm.MatchValue(value=document_id),
                        ),
                    ]
                )
            ),
        )

    def count_document(self, *, account_id: str, document_id: str) -> int:
        qm = self._qm
        result = self._client.count(
            collection_name=self.COLLECTION,
            count_filter=qm.Filter(
                must=[
                    qm.FieldCondition(
                        key="account_id",
                        match=qm.MatchValue(value=account_id),
                    ),
                    qm.FieldCondition(
                        key="document_id",
                        match=qm.MatchValue(value=document_id),
                    ),
                    qm.FieldCondition(
                        key="active",
                        match=qm.MatchValue(value=True),
                    ),
                ]
            ),
            exact=True,
        )
        return int(result.count)

    def verify_document_indexed(
        self, *, account_id: str, document_id: str, expected_chunks: int
    ) -> bool:
        if expected_chunks <= 0:
            return False
        return (
            self.count_document(account_id=account_id, document_id=document_id)
            == expected_chunks
        )


class NullVectorStore:
    """No-op dense store — lexical-only fallback."""

    def upsert_chunks(self, **kwargs: Any) -> None:
        return None

    def search(self, **kwargs: Any) -> list[EvidenceChunk]:
        return []

    def delete_document(self, **kwargs: Any) -> None:
        return None

    def count_document(self, **kwargs: Any) -> int:
        return 0

    def verify_document_indexed(self, **kwargs: Any) -> bool:
        return False

    def close(self) -> None:
        return None


_lock = threading.Lock()
_stores: dict[str, QdrantVectorStore] = {}


def get_vector_store(
    settings: ApplicationSettings,
    *,
    dimensions: int | None = None,
) -> VectorStore:
    """Process-wide singleton — Qdrant local path allows only one open client."""
    backend = settings.vector_store_backend.lower().strip()
    if backend in {"null", "none", "off"}:
        return NullVectorStore()
    if backend not in {"qdrant", "local"}:
        raise ValueError(
            f"Unsupported VECTOR_STORE_BACKEND={settings.vector_store_backend!r}"
        )
    dims = dimensions
    if dims is None:
        dims = build_embedding_provider(settings).dimensions
    fingerprint = embedding_fingerprint(settings, dimensions=dims)
    key = f"{settings.vector_path.resolve()}::{fingerprint}"
    with _lock:
        existing = _stores.get(key)
        if existing is not None:
            return existing
        # Close any other store on the same path (Qdrant exclusive lock).
        stale_keys = [
            k for k in _stores if k.startswith(str(settings.vector_path.resolve()))
        ]
        for stale in stale_keys:
            _stores.pop(stale).close()
        store = QdrantVectorStore(
            settings.vector_path,
            dimensions=dims,
            fingerprint=fingerprint,
        )
        _stores[key] = store
        return store


def reset_vector_store_for_tests() -> None:
    with _lock:
        for store in _stores.values():
            store.close()
        _stores.clear()


def _collection_name(fingerprint: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", fingerprint).strip("_").lower()
    slug = slug[:80] or "default"
    return f"limen_{slug}"


def _point_id(chunk_id: str) -> str:
    """Qdrant accepts UUID or unsigned int; use deterministic UUID from chunk_id."""
    import hashlib
    from uuid import UUID

    digest = hashlib.sha256(chunk_id.encode("utf-8")).hexdigest()
    return str(UUID(hex=digest[:32]))
