"""Shared FastAPI dependencies. Transport wiring only."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from limen.auth import Account, AuthService, SessionInvalid
from limen.config.settings import ApplicationSettings, get_settings
from limen.conversation.call_service import CallService
from limen.intelligence.providers.factory import build_llm_provider
from limen.knowledge.contracts import EmbeddingProvider, EvidenceRetriever, RetrievalConfig
from limen.knowledge.deletion import KnowledgeDeletionService
from limen.knowledge.embeddings import (
    build_embedding_provider,
    default_dense_min_score,
)
from limen.knowledge.hybrid import HybridEvidenceRetriever
from limen.knowledge.ingestion import KnowledgeIngestionService
from limen.knowledge.retrieval import KnowledgeRetrievalService
from limen.knowledge.vector_store import VectorStore, get_vector_store
from limen.persistence.database import get_database
from limen.persistence.repositories import (
    SqliteAccountRepository,
    SqliteCallRepository,
    SqliteKnowledgeRepository,
    SqliteTraceRepository,
)
from limen.voice.contracts import STTProvider, TTSProvider
from limen.voice.stt import build_stt_provider
from limen.voice.tts import build_tts_provider


def settings_dependency() -> ApplicationSettings:
    return get_settings()


Settings = Annotated[ApplicationSettings, Depends(settings_dependency)]


def auth_service_dependency(settings: Settings) -> AuthService:
    database = get_database(settings)
    return AuthService(
        SqliteAccountRepository(database),
        session_ttl=settings.auth_session_ttl(),
    )


Auth = Annotated[AuthService, Depends(auth_service_dependency)]


def session_token(request: Request, settings: Settings) -> str | None:
    return request.cookies.get(settings.auth_cookie_name)


def optional_account(
    auth: Auth,
    token: Annotated[str | None, Depends(session_token)],
) -> Account | None:
    """Resolves the caller when a valid session cookie is present."""
    if not token:
        return None
    try:
        return auth.authenticate(token)
    except SessionInvalid:
        return None


def require_account(
    auth: Auth,
    token: Annotated[str | None, Depends(session_token)],
) -> Account:
    """Guards every client-owned resource."""
    if not token:
        raise _unauthorized()
    try:
        return auth.authenticate(token)
    except SessionInvalid:
        raise _unauthorized() from None


CurrentAccount = Annotated[Account, Depends(require_account)]
OptionalAccount = Annotated[Account | None, Depends(optional_account)]


def knowledge_repository(settings: Settings) -> SqliteKnowledgeRepository:
    return SqliteKnowledgeRepository(get_database(settings))


def embedding_provider_dependency(settings: Settings) -> EmbeddingProvider:
    return build_embedding_provider(settings)


def vector_store_dependency(settings: Settings) -> VectorStore:
    emb = build_embedding_provider(settings)
    return get_vector_store(settings, dimensions=emb.dimensions)


def retrieval_config(settings: ApplicationSettings) -> RetrievalConfig:
    return RetrievalConfig(
        dense_top_k=settings.dense_top_k,
        lexical_top_k=settings.lexical_top_k,
        final_top_k=settings.final_top_k,
        rrf_k=settings.rrf_k,
        dense_min_score=default_dense_min_score(settings),
    )


def hybrid_retriever(settings: ApplicationSettings) -> HybridEvidenceRetriever:
    knowledge = SqliteKnowledgeRepository(get_database(settings))
    embeddings = build_embedding_provider(settings)
    vectors = get_vector_store(settings, dimensions=embeddings.dimensions)
    return HybridEvidenceRetriever(
        lexical=KnowledgeRetrievalService(knowledge),
        vectors=vectors,
        embeddings=embeddings,
        config=retrieval_config(settings),
    )


def call_service_dependency(request: Request, settings: Settings) -> CallService:
    database = get_database(settings)
    llm = getattr(request.app.state, "llm", None) or build_llm_provider(settings)
    return CallService(
        calls=SqliteCallRepository(database),
        traces=SqliteTraceRepository(database),
        retrieval=hybrid_retriever(settings),
        llm=llm,
    )


def knowledge_ingestion_dependency(settings: Settings) -> KnowledgeIngestionService:
    embeddings = build_embedding_provider(settings)
    return KnowledgeIngestionService(
        knowledge_repository(settings),
        settings,
        embeddings=embeddings,
        vector_store=get_vector_store(settings, dimensions=embeddings.dimensions),
    )


def knowledge_deletion_dependency(settings: Settings) -> KnowledgeDeletionService:
    embeddings = build_embedding_provider(settings)
    return KnowledgeDeletionService(
        knowledge_repository(settings),
        vector_store=get_vector_store(settings, dimensions=embeddings.dimensions),
    )


def knowledge_retrieval_dependency(settings: Settings) -> EvidenceRetriever:
    return hybrid_retriever(settings)


CallSvc = Annotated[CallService, Depends(call_service_dependency)]
KnowledgeIngest = Annotated[
    KnowledgeIngestionService, Depends(knowledge_ingestion_dependency)
]
KnowledgeDelete = Annotated[
    KnowledgeDeletionService, Depends(knowledge_deletion_dependency)
]
KnowledgeRetrieve = Annotated[
    EvidenceRetriever, Depends(knowledge_retrieval_dependency)
]


def stt_dependency(request: Request, settings: Settings) -> STTProvider:
    return getattr(request.app.state, "stt", None) or build_stt_provider(settings)


def tts_dependency(request: Request, settings: Settings) -> TTSProvider:
    return getattr(request.app.state, "tts", None) or build_tts_provider(settings)


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": "session_invalid", "message": "Sign in to continue."},
    )
