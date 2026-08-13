"""Challenge runtime profile — one switch for the real Tech Sphere stack.

Set ``LIMEN_RUNTIME_PROFILE=challenge`` (or call ``apply_runtime_profile()``)
before constructing ``ApplicationSettings``. Explicit environment variables
always win over profile defaults (setdefault semantics).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

PROFILE_CHALLENGE = "challenge"
PROFILE_DEVELOPMENT = "development"
PROFILE_CI = "ci"

# Deterministic challenge stack. No stubs.
CHALLENGE_ENV_DEFAULTS: dict[str, str] = {
    "APP_ENV": "challenge",
    "LLM_PROVIDER": "ollama",
    "LLM_MODEL": "phi3.5",
    "LLM_BASE_URL": "http://127.0.0.1:11434",
    "LLM_TIMEOUT_S": "45",
    "STT_PROVIDER": "faster_whisper",
    "STT_MODEL": "Systran/faster-whisper-small",
    "STT_DEVICE": "cuda",
    "STT_COMPUTE_TYPE": "float16",
    "STT_ALLOW_CPU_FALLBACK": "0",
    "TTS_PROVIDER": "piper",
    "TTS_MODEL": "es_MX-claude-high",
    "TTS_VOICE": "es_MX-claude-high",
    "TTS_MODEL_PATH": str(ROOT / "runtime" / "models" / "piper"),
    "EMBEDDING_PROVIDER": "sentence-transformers",
    "EMBEDDING_MODEL": "intfloat/multilingual-e5-small",
    "VECTOR_STORE_BACKEND": "qdrant",
    "DATABASE_PATH": str(ROOT / "runtime" / "db" / "limen.db"),
    "VECTOR_PATH": str(ROOT / "runtime" / "vectors"),
    "DOCUMENT_PATH": str(ROOT / "runtime" / "documents"),
    "LOG_PATH": str(ROOT / "runtime" / "logs"),
    "AUDIO_PATH": str(ROOT / "runtime" / "audio"),
}


def current_runtime_profile() -> str:
    raw = (os.environ.get("LIMEN_RUNTIME_PROFILE") or PROFILE_DEVELOPMENT).strip().lower()
    if raw in {PROFILE_CHALLENGE, "prod", "production"}:
        return PROFILE_CHALLENGE
    if raw in {PROFILE_CI, "test", "testing"}:
        return PROFILE_CI
    return PROFILE_DEVELOPMENT


_PROVIDER_KEYS = {
    "LLM_PROVIDER",
    "STT_PROVIDER",
    "TTS_PROVIDER",
    "EMBEDDING_PROVIDER",
}


def apply_runtime_profile(*, force: bool = False) -> str:
    """Apply profile defaults into ``os.environ``.

    Returns the active profile name. Under challenge profile, stub provider
    values are always replaced (they must never silently run as challenge).
    Other explicit non-empty env values win unless ``force=True``.
    """
    profile = current_runtime_profile()
    if profile != PROFILE_CHALLENGE:
        return profile
    for key, value in CHALLENGE_ENV_DEFAULTS.items():
        current = os.environ.get(key, "")
        if (
            force
            or current == ""
            or (key in _PROVIDER_KEYS and current.lower() == "stub")
            or (key == "TTS_MODEL" and current.lower() in {"stub", "stub-tts"})
            or key not in os.environ
        ):
            os.environ[key] = value
    # Prefer local E5 checkout when present and unset.
    if not os.environ.get("EMBEDDING_MODEL_PATH"):
        for candidate in (
            ROOT / ".cache" / "models" / "multilingual-e5-small",
            ROOT / "runtime" / "models" / "multilingual-e5-small",
        ):
            if (candidate / "model.safetensors").is_file() or (candidate / "config.json").is_file():
                os.environ["EMBEDDING_MODEL_PATH"] = str(candidate)
                break
    return profile


def challenge_stub_violations(settings: Any) -> list[str]:
    """Return provider fields that are still stubs under challenge profile."""
    violations: list[str] = []
    if str(getattr(settings, "llm_provider", "")).lower() == "stub":
        violations.append("LLM_PROVIDER=stub")
    if str(getattr(settings, "stt_provider", "")).lower() == "stub":
        violations.append("STT_PROVIDER=stub")
    if str(getattr(settings, "tts_provider", "")).lower() == "stub":
        violations.append("TTS_PROVIDER=stub")
    if str(getattr(settings, "embedding_provider", "")).lower() == "stub":
        violations.append("EMBEDDING_PROVIDER=stub")
    return violations


def is_challenge_profile(settings: Any | None = None) -> bool:
    if settings is not None:
        profile = str(getattr(settings, "runtime_profile", "") or "").lower()
        if profile == PROFILE_CHALLENGE:
            return True
    return current_runtime_profile() == PROFILE_CHALLENGE
