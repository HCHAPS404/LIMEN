"""Knowledge administration transport."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from apps.api.dependencies import (
    CurrentAccount,
    KnowledgeDelete,
    KnowledgeIngest,
    KnowledgeRetrieve,
    knowledge_repository,
    settings_dependency,
)
from apps.api.schemas.knowledge import (
    DuplicateDocumentResponse,
    EvidenceChunkResponse,
    KnowledgeDocumentResponse,
    RetrievalProbeResponse,
)
from limen.config.settings import get_settings
from limen.knowledge.deletion import IncompletePurgeError
from limen.knowledge.ingestion import DuplicateDocumentError, KnowledgeIngestionService
from limen.knowledge.jobs import get_knowledge_job_runner
from limen.persistence.repositories.knowledge import SqliteKnowledgeRepository

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


def _schedule_processing(
    account_id: str,
    document_id: str,
    database_path: str,
) -> None:
    """Background entrypoint with a dedicated DB connection (no global singleton).

    Vector store uses the process-wide Qdrant singleton (local path is exclusive).
    """
    from pathlib import Path

    from limen.knowledge.embeddings import build_embedding_provider
    from limen.knowledge.vector_store import get_vector_store
    from limen.persistence.database import Database

    settings = get_settings()
    db = Database(Path(database_path))
    db.initialize()
    try:
        embeddings = build_embedding_provider(settings)
        service = KnowledgeIngestionService(
            SqliteKnowledgeRepository(db),
            settings,
            embeddings=embeddings,
            vector_store=get_vector_store(settings, dimensions=embeddings.dimensions),
        )
        service.process_document(account_id=account_id, document_id=document_id)
    finally:
        db.close()


@router.get("/documents", response_model=list[KnowledgeDocumentResponse])
async def list_documents(account: CurrentAccount) -> list[KnowledgeDocumentResponse]:
    settings = settings_dependency()
    rows = knowledge_repository(settings).list_documents(account.account_id)
    return [KnowledgeDocumentResponse.model_validate(row) for row in rows]


@router.post(
    "/documents",
    response_model=KnowledgeDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    account: CurrentAccount,
    ingest: KnowledgeIngest,
    file: Annotated[UploadFile, File()],
) -> KnowledgeDocumentResponse:
    payload = await file.read()
    if not payload:
        raise HTTPException(
            status_code=422,
            detail={"code": "empty_document", "message": "Uploaded file is empty"},
        )
    try:
        document = ingest.accept_upload(
            account_id=account.account_id,
            filename=file.filename or "document.txt",
            payload=payload,
        )
    except DuplicateDocumentError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=DuplicateDocumentResponse(
                message=str(error),
                document=KnowledgeDocumentResponse.model_validate(error.existing),
            ).model_dump(mode="json"),
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail={"code": "document_rejected", "message": str(error)},
        ) from error

    settings = settings_dependency()
    get_knowledge_job_runner().submit(
        _schedule_processing,
        account.account_id,
        document["document_id"],
        str(settings.database_path),
    )
    return KnowledgeDocumentResponse.model_validate(document)


@router.get("/documents/{document_id}", response_model=KnowledgeDocumentResponse)
async def get_document(
    document_id: str,
    account: CurrentAccount,
) -> KnowledgeDocumentResponse:
    settings = settings_dependency()
    found = knowledge_repository(settings).get_document(account.account_id, document_id)
    if found is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "document_not_found", "message": "Document not found"},
        )
    return KnowledgeDocumentResponse.model_validate(found)


@router.delete(
    "/documents/{document_id}",
    response_model=KnowledgeDocumentResponse,
)
async def delete_document(
    document_id: str,
    account: CurrentAccount,
    deletion: KnowledgeDelete,
) -> KnowledgeDocumentResponse:
    try:
        removed = deletion.delete(account_id=account.account_id, document_id=document_id)
    except IncompletePurgeError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "purge_incomplete", "message": str(error)},
        ) from error
    if removed is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "document_not_found", "message": "Document not found"},
        )
    return KnowledgeDocumentResponse.model_validate(removed)


@router.get("/retrieval-probe", response_model=RetrievalProbeResponse)
async def retrieval_probe(
    account: CurrentAccount,
    retrieve: KnowledgeRetrieve,
    query: str = "seguimiento postoperatorio",
) -> RetrievalProbeResponse:
    chunks = retrieve.retrieve(account_id=account.account_id, query=query, limit=8)
    return RetrievalProbeResponse(
        query=query,
        executed_at=datetime.now(tz=UTC).isoformat(),
        chunks=[
            EvidenceChunkResponse(
                document_id=chunk.document_id,
                chunk_id=chunk.chunk_id,
                text=chunk.text,
                source_name=chunk.source_name,
                filename=chunk.filename,
                page=chunk.page,
                section=chunk.section,
                score=chunk.score,
                version=chunk.version,
                version_id=chunk.version_id,
                content_hash=chunk.content_hash,
                active=chunk.active,
                retrieval_modes=list(chunk.retrieval_modes),
            )
            for chunk in chunks
        ],
    )
