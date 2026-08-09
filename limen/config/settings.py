"""Typed application settings loaded from environment / .env."""

from datetime import timedelta
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ApplicationSettings(BaseSettings):
    """Single typed settings object for LIMEN."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = Field(default="development", alias="APP_ENV")
    # development | ci | challenge — challenge applies real-provider defaults.
    runtime_profile: str = Field(default="development", alias="LIMEN_RUNTIME_PROFILE")
    app_host: str = Field(default="127.0.0.1", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    cors_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        alias="CORS_ORIGINS",
    )

    llm_provider: str = Field(default="stub", alias="LLM_PROVIDER")
    llm_model: str = Field(default="stub-model", alias="LLM_MODEL")
    llm_api_key: str = Field(default="", alias="LLM_API_KEY")
    llm_base_url: str = Field(default="", alias="LLM_BASE_URL")
    llm_temperature: float = Field(default=0.2, alias="LLM_TEMPERATURE")
    llm_max_tokens: int | None = Field(default=256, alias="LLM_MAX_TOKENS")
    # Clinical hot-path timeout — hung LLM must not block indefinitely.
    llm_timeout_s: float = Field(default=45.0, alias="LLM_TIMEOUT_S")
    # Optional secondary LLM for non-critical experiments (disabled by default).
    llm_secondary_enabled: bool = Field(default=False, alias="LLM_SECONDARY_ENABLED")
    llm_secondary_model: str = Field(default="", alias="LLM_SECONDARY_MODEL")

    stt_provider: str = Field(default="stub", alias="STT_PROVIDER")
    stt_model: str = Field(default="stub-stt", alias="STT_MODEL")
    stt_api_key: str = Field(default="", alias="STT_API_KEY")
    stt_device: str = Field(default="auto", alias="STT_DEVICE")
    stt_compute_type: str = Field(default="default", alias="STT_COMPUTE_TYPE")
    # When STT_DEVICE=cuda, default false (no silent CPU success). Override via env.
    stt_allow_cpu_fallback: bool = Field(default=True, alias="STT_ALLOW_CPU_FALLBACK")
    stt_model_path: str = Field(default="", alias="STT_MODEL_PATH")
    stt_timeout_s: float = Field(default=60.0, alias="STT_TIMEOUT_S")

    tts_provider: str = Field(default="stub", alias="TTS_PROVIDER")
    tts_model: str = Field(default="stub-tts", alias="TTS_MODEL")
    tts_voice: str = Field(default="default", alias="TTS_VOICE")
    tts_model_path: str = Field(default="", alias="TTS_MODEL_PATH")
    tts_timeout_s: float = Field(default=60.0, alias="TTS_TIMEOUT_S")

    embedding_provider: str = Field(default="stub", alias="EMBEDDING_PROVIDER")
    embedding_model: str = Field(
        default="intfloat/multilingual-e5-small",
        alias="EMBEDDING_MODEL",
    )
    # Optional local checkout/cache. When set, takes precedence over Hub id.
    embedding_model_path: str = Field(default="", alias="EMBEDDING_MODEL_PATH")
    embedding_dimensions: int = Field(default=64, alias="EMBEDDING_DIMENSIONS")
    vector_store_backend: str = Field(default="qdrant", alias="VECTOR_STORE_BACKEND")

    # Hybrid retrieval (RRF) — kept centralized, not scattered as magic numbers.
    dense_top_k: int = Field(default=8, alias="DENSE_TOP_K")
    lexical_top_k: int = Field(default=8, alias="LEXICAL_TOP_K")
    final_top_k: int = Field(default=5, alias="FINAL_TOP_K")
    rrf_k: int = Field(default=60, alias="RRF_K")
    # None = provider-aware baseline (stub 0.35 / e5 calibrated). Explicit override wins.
    dense_min_score: float | None = Field(default=None, alias="DENSE_MIN_SCORE")

    database_path: Path = Field(default=Path("./runtime/db/limen.db"), alias="DATABASE_PATH")
    vector_path: Path = Field(default=Path("./runtime/vectors"), alias="VECTOR_PATH")
    document_path: Path = Field(default=Path("./runtime/documents"), alias="DOCUMENT_PATH")
    log_path: Path = Field(default=Path("./runtime/logs"), alias="LOG_PATH")
    audio_path: Path = Field(default=Path("./runtime/audio"), alias="AUDIO_PATH")

    max_upload_mb: int = Field(default=25, alias="MAX_UPLOAD_MB")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Client accounts (ADR-0004). The cookie is httpOnly in every environment;
    # `AUTH_COOKIE_SECURE` only controls the HTTPS-only flag, which must be on
    # in production and off for plain-HTTP local development.
    auth_session_ttl_hours: int = Field(default=168, alias="AUTH_SESSION_TTL_HOURS")
    auth_cookie_name: str = Field(default="limen_session", alias="AUTH_COOKIE_NAME")
    auth_cookie_secure: bool = Field(default=False, alias="AUTH_COOKIE_SECURE")

    # Optional local demo account created by bootstrap so a cold start can sign
    # in immediately. Left empty means "create nothing".
    demo_email: str = Field(default="", alias="LIMEN_DEMO_EMAIL")
    demo_password: str = Field(default="", alias="LIMEN_DEMO_PASSWORD")
    demo_display_name: str = Field(default="LIMEN Demo", alias="LIMEN_DEMO_NAME")

    # Conversation continuity (PHASE 6.3) — bounded memory, not full transcript dump.
    conversation_recent_turns: int = Field(default=6, alias="CONVERSATION_RECENT_TURNS")
    conversation_context_token_budget: int = Field(
        default=1800,
        alias="CONVERSATION_CONTEXT_TOKEN_BUDGET",
    )

    def auth_session_ttl(self) -> timedelta:
        return timedelta(hours=self.auth_session_ttl_hours)

    def has_demo_account(self) -> bool:
        return bool(self.demo_email and self.demo_password)

    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def ensure_runtime_dirs(self) -> None:
        for path in (
            self.database_path.parent,
            self.vector_path,
            self.document_path,
            self.log_path,
            self.audio_path,
        ):
            path.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> ApplicationSettings:
    from limen.config.challenge_profile import apply_runtime_profile

    apply_runtime_profile()
    return ApplicationSettings()
