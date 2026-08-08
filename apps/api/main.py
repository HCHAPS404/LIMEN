"""LIMEN FastAPI entrypoint — transport only; domain logic lives in limen/."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from apps.api.routers import auth_router
from limen import __version__
from limen.auth import AuthService
from limen.config.logging import configure_logging
from limen.config.settings import ApplicationSettings, get_settings
from limen.intelligence.providers import build_llm_provider
from limen.persistence.database import get_database
from limen.persistence.repositories import SqliteAccountRepository


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    app_env: str
    llm_provider: str
    llm_model: str
    database: dict[str, str] = Field(default_factory=dict)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)
    settings.ensure_runtime_dirs()
    db = get_database(settings)
    db.initialize()
    # Expired sessions accumulate while the API is down; clear them at boot so a
    # stale cookie cannot outlive its TTL.
    AuthService(
        SqliteAccountRepository(db),
        session_ttl=settings.auth_session_ttl(),
    ).purge_expired_sessions()
    # Ensure configured providers construct at boot.
    app.state.settings = settings
    app.state.llm = build_llm_provider(settings)
    yield


def create_app(settings: ApplicationSettings | None = None) -> FastAPI:
    cfg = settings or get_settings()
    application = FastAPI(
        title="LIMEN API",
        version=__version__,
        description="Voice-first postoperative follow-up — Tech Sphere Challenge 2026",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.cors_origin_list(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(auth_router)

    @application.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        settings = get_settings()
        db = get_database(settings)
        return HealthResponse(
            status="ok",
            version=__version__,
            app_env=settings.app_env,
            llm_provider=settings.llm_provider,
            llm_model=settings.llm_model,
            database=db.health(),
        )

    return application


app = create_app()
