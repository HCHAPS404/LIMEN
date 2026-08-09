"""LIMEN FastAPI entrypoint — transport only; domain logic lives in limen/."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from apps.api.routers import (
    auth_router,
    calls_router,
    knowledge_router,
    metrics_router,
    traces_router,
)
from limen import __version__
from limen.auth import AuthService
from limen.config.logging import configure_logging
from limen.config.settings import ApplicationSettings, get_settings
from limen.intelligence.llm_status import get_llm_runtime_status, probe_llm_runtime
from limen.intelligence.providers import build_llm_provider
from limen.knowledge.embeddings import build_embedding_provider
from limen.knowledge.ingestion import KnowledgeIngestionService
from limen.knowledge.jobs import get_knowledge_job_runner, shutdown_knowledge_job_runner
from limen.knowledge.vector_store import get_vector_store, reset_vector_store_for_tests
from limen.persistence.database import get_database
from limen.persistence.repositories import SqliteAccountRepository, SqliteKnowledgeRepository
from limen.voice.stt import build_stt_provider
from limen.voice.tts import build_tts_provider


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    app_env: str
    runtime_profile: str = "development"
    llm_provider: str
    llm_model: str
    degraded_llm_mode: bool = False
    stub_providers: list[str] = Field(default_factory=list)
    database: dict[str, str] = Field(default_factory=dict)


class ReadyResponse(BaseModel):
    status: str
    checks: dict[str, str]


class ProvidersResponse(BaseModel):
    runtime_profile: str = "development"
    llm: dict[str, object]
    stt: dict[str, object]
    tts: dict[str, object]
    embedding: dict[str, object]
    vector_store: dict[str, object] = Field(default_factory=dict)
    stub_providers: list[str] = Field(default_factory=list)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)
    settings.ensure_runtime_dirs()
    db = get_database(settings)
    db.initialize()
    AuthService(
        SqliteAccountRepository(db),
        session_ttl=settings.auth_session_ttl(),
    ).purge_expired_sessions()
    # Restart policy: never leave PROCESSING as a silent AVAILABLE candidate.
    KnowledgeIngestionService(
        SqliteKnowledgeRepository(db),
        settings,
    ).fail_interrupted_processing()
    # Open the local vector store once at startup (Qdrant path is exclusive).
    try:
        emb = build_embedding_provider(settings)
        get_vector_store(settings, dimensions=emb.dimensions)
    except Exception:  # noqa: BLE001 — vector init failure surfaces in readiness later
        pass
    get_knowledge_job_runner()
    # Ensure CUDA 12 pip libs are visible before any STT provider load.
    try:
        from limen.voice.cuda_runtime import ensure_cuda12_library_path

        ensure_cuda12_library_path()
    except Exception:  # noqa: BLE001
        pass
    app.state.settings = settings
    app.state.llm = build_llm_provider(settings)
    app.state.stt = build_stt_provider(settings)
    app.state.tts = build_tts_provider(settings)
    # Probe LLM reachability — never crash the app if Ollama is down.
    app.state.llm_status = await probe_llm_runtime(settings, app.state.llm)
    try:
        yield
    finally:
        shutdown_knowledge_job_runner(wait=True)
        reset_vector_store_for_tests()


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
    application.include_router(calls_router)
    application.include_router(knowledge_router)
    application.include_router(traces_router)
    application.include_router(metrics_router)

    @application.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        from limen.config.challenge_profile import challenge_stub_violations

        settings = get_settings()
        db = get_database(settings)
        llm_status = get_llm_runtime_status()
        stubs = challenge_stub_violations(settings)
        return HealthResponse(
            status="ok",
            version=__version__,
            app_env=settings.app_env,
            runtime_profile=settings.runtime_profile,
            llm_provider=settings.llm_provider,
            llm_model=settings.llm_model,
            degraded_llm_mode=bool(llm_status.degraded_mode),
            stub_providers=stubs,
            database=db.health(),
        )

    @application.get("/health/ready", response_model=ReadyResponse)
    async def ready() -> ReadyResponse:
        from limen.config.challenge_profile import (
            challenge_stub_violations,
            is_challenge_profile,
        )

        settings = get_settings()
        checks: dict[str, str] = {}
        try:
            db = get_database(settings)
            checks["database"] = db.health().get("database", "ok")
        except Exception as error:  # noqa: BLE001
            checks["database"] = f"error:{error}"
        try:
            build_llm_provider(settings)
            llm_status = get_llm_runtime_status()
            if settings.llm_provider.lower().strip() == "ollama" and llm_status.degraded_mode:
                checks["llm"] = "degraded"
            else:
                checks["llm"] = "ok"
        except Exception as error:  # noqa: BLE001
            checks["llm"] = f"error:{error}"
        try:
            build_stt_provider(settings)
            checks["stt"] = "ok"
        except Exception as error:  # noqa: BLE001
            checks["stt"] = f"error:{error}"
        try:
            build_tts_provider(settings)
            checks["tts"] = "ok"
        except Exception as error:  # noqa: BLE001
            checks["tts"] = f"error:{error}"
        if is_challenge_profile(settings):
            stubs = challenge_stub_violations(settings)
            if stubs:
                checks["challenge_stubs"] = "error:" + ",".join(stubs)
        # Degraded LLM is allowed: app remains usable for safety/RAG/templates.
        hard_fail = any(
            (not value.startswith("ok") and value != "degraded")
            for key, value in checks.items()
            if key != "llm"
        ) or checks.get("llm", "").startswith("error:")
        status = "degraded" if hard_fail or checks.get("llm") == "degraded" else "ready"
        return ReadyResponse(status=status, checks=checks)

    @application.get("/health/providers", response_model=ProvidersResponse)
    async def providers() -> ProvidersResponse:
        from limen.config.challenge_profile import challenge_stub_violations

        settings = get_settings()
        llm_status = get_llm_runtime_status()
        stt = build_stt_provider(settings)
        tts = build_tts_provider(settings)
        stubs = challenge_stub_violations(settings)
        stt_health: dict[str, object] = {
            "provider": settings.stt_provider,
            "model": settings.stt_model,
            "configured": settings.stt_provider,
        }
        tts_health: dict[str, object] = {
            "provider": settings.tts_provider,
            "model": settings.tts_model,
            "voice": settings.tts_voice,
            "configured": settings.tts_provider,
        }
        try:
            stt_probe = await stt.health()
            stt_health.update(
                {
                    "reachable": bool(stt_probe.get("reachable", stt_probe.get("ok"))),
                    "degraded_mode": bool(stt_probe.get("degraded", not stt_probe.get("ok"))),
                    "degraded": bool(stt_probe.get("degraded", not stt_probe.get("ok"))),
                    "configured_device": stt_probe.get(
                        "configured_device", settings.stt_device
                    ),
                    "requested_device": stt_probe.get("requested_device"),
                    "actual_device": stt_probe.get("actual_device"),
                    "compute_type": stt_probe.get("compute_type"),
                    "fallback_reason": stt_probe.get("fallback_reason"),
                    "last_error": stt_probe.get("error"),
                    "ok": bool(stt_probe.get("ok")),
                }
            )
        except Exception as exc:  # noqa: BLE001
            stt_health.update(
                {"reachable": False, "degraded_mode": True, "last_error": str(exc)}
            )
        try:
            tts_probe = await tts.health()
            tts_health.update(
                {
                    "reachable": bool(tts_probe.get("ok")),
                    "degraded_mode": not bool(tts_probe.get("ok")),
                    "last_error": tts_probe.get("error"),
                }
            )
        except Exception as exc:  # noqa: BLE001
            tts_health.update(
                {"reachable": False, "degraded_mode": True, "last_error": str(exc)}
            )
        vector_info: dict[str, object] = {
            "backend": settings.vector_store_backend,
            "path": str(settings.vector_path),
        }
        try:
            emb = build_embedding_provider(settings)
            store = get_vector_store(settings, dimensions=emb.dimensions)
            vector_info["reachable"] = True
            vector_info["type"] = type(store).__name__
            vector_info["degraded"] = False
        except Exception as exc:  # noqa: BLE001
            vector_info["reachable"] = False
            vector_info["degraded"] = True
            vector_info["last_error"] = str(exc)
        return ProvidersResponse(
            runtime_profile=settings.runtime_profile,
            llm={
                "provider": settings.llm_provider,
                "model": settings.llm_model,
                "configured": settings.llm_provider,
                "configured_provider": llm_status.configured_provider,
                "configured_model": llm_status.configured_model,
                "reachable": llm_status.reachable,
                "degraded_mode": llm_status.degraded_mode,
                "last_provider_error": llm_status.last_provider_error,
                "timeout_s": settings.llm_timeout_s,
                "secondary_enabled": settings.llm_secondary_enabled,
                "secondary_model": settings.llm_secondary_model or None,
                "safety_fallback": "deterministic_templates",
            },
            stt=stt_health,
            tts=tts_health,
            embedding={
                "provider": settings.embedding_provider,
                "model": settings.embedding_model,
                "configured": settings.embedding_provider,
                "model_path": settings.embedding_model_path or None,
                "degraded": settings.embedding_provider.lower() == "stub",
            },
            vector_store=vector_info,
            stub_providers=stubs,
        )

    return application


app = create_app()
