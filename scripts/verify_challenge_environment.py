#!/usr/bin/env python3
"""Challenge runtime preflight.

Sets LIMEN_RUNTIME_PROFILE=challenge (unless already set) and verifies the
real stack. Ends with READY_FOR_CHALLENGE_RUNTIME=TRUE/FALSE.

Stubs can never make this TRUE.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("LIMEN_RUNTIME_PROFILE", "challenge")

from limen.config.challenge_profile import (  # noqa: E402
    apply_runtime_profile,
    challenge_stub_violations,
)
from limen.config.settings import ApplicationSettings  # noqa: E402
from limen.voice.cuda_runtime import ensure_cuda12_library_path  # noqa: E402


def _ollama(base: str) -> dict[str, object]:
    url = base.rstrip("/") + "/api/tags"
    try:
        with urllib.request.urlopen(url, timeout=3) as resp:  # noqa: S310
            payload = json.loads(resp.read().decode("utf-8"))
        names = [str(m.get("name") or "") for m in payload.get("models") or []]
        return {"reachable": True, "models": names}
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        return {"reachable": False, "error": f"{type(exc).__name__}:{exc}", "models": []}


def _node_ok() -> dict[str, object]:
    node = shutil.which("node")
    npm = shutil.which("npm")
    web_modules = (ROOT / "apps" / "web" / "node_modules").is_dir()
    return {
        "node": node or "",
        "npm": npm or "",
        "web_node_modules": web_modules,
        "ok": bool(node and npm and web_modules),
    }


def _piper_voice(settings: ApplicationSettings) -> dict[str, object]:
    base = Path(settings.tts_model_path or ROOT / "runtime" / "models" / "piper")
    voice = settings.tts_voice or "es_MX-claude-high"
    onnx = base / f"{voice}.onnx"
    # Piper often ships as voice.onnx + voice.onnx.json
    alt = list(base.glob(f"*{voice}*.onnx")) + list(base.glob("*.onnx"))
    found = onnx if onnx.is_file() else (alt[0] if alt else None)
    return {
        "path": str(base),
        "voice": voice,
        "onnx": str(found) if found else None,
        "ok": found is not None and found.is_file(),
    }


def main() -> int:
    profile = apply_runtime_profile()
    # Fresh settings without cached development defaults.
    from limen.config import settings as settings_module

    settings_module.get_settings.cache_clear()
    settings = ApplicationSettings()

    report: dict[str, object] = {
        "runtime_profile": profile,
        "python": sys.version.split()[0],
        "llm": {"provider": settings.llm_provider, "model": settings.llm_model},
        "stt": {
            "provider": settings.stt_provider,
            "model": settings.stt_model,
            "device": settings.stt_device,
        },
        "tts": {
            "provider": settings.tts_provider,
            "voice": settings.tts_voice,
            "model_path": str(settings.tts_model_path),
        },
        "embedding": {
            "provider": settings.embedding_provider,
            "model": settings.embedding_model,
            "model_path": settings.embedding_model_path or None,
        },
        "vector_store": settings.vector_store_backend,
    }

    ready = True
    reasons: list[str] = []

    stubs = challenge_stub_violations(settings)
    report["stub_violations"] = stubs
    if stubs:
        ready = False
        reasons.extend(stubs)

    # Writable runtime paths
    try:
        settings.ensure_runtime_dirs()
        report["runtime_dirs"] = "ok"
    except OSError as exc:
        ready = False
        reasons.append(f"runtime_dirs:{exc}")
        report["runtime_dirs"] = f"error:{exc}"

    # SQLite
    try:
        from limen.persistence.database import Database

        db = Database(settings.database_path)
        db.initialize()
        report["sqlite"] = db.health()
        db.close()
    except Exception as exc:  # noqa: BLE001
        ready = False
        reasons.append(f"sqlite:{exc}")
        report["sqlite"] = {"error": str(exc)}

    # Ollama + phi3.5
    ollama = _ollama(settings.llm_base_url or "http://127.0.0.1:11434")
    report["ollama"] = ollama
    if not ollama.get("reachable"):
        ready = False
        reasons.append("ollama_unreachable")
    else:
        models = [str(m) for m in (ollama.get("models") or [])]  # type: ignore[arg-type]
        if not any("phi3.5" in m or m.startswith("phi3.5") for m in models):
            ready = False
            reasons.append("phi3.5_not_pulled")

    # CUDA + STT
    cuda12 = ensure_cuda12_library_path()
    report["cuda12_pip_libs"] = cuda12
    try:
        import asyncio

        from limen.voice.stt import build_stt_provider

        stt = build_stt_provider(settings)
        stt_health = asyncio.run(stt.health())  # type: ignore[misc]
        report["stt_health"] = stt_health
        if not stt_health.get("ok"):
            ready = False
            reasons.append(f"stt:{stt_health.get('error')}")
        if settings.stt_device.lower() == "cuda" and stt_health.get("actual_device") != "cuda":
            ready = False
            reasons.append(f"stt_not_cuda:{stt_health.get('actual_device')}")
        if not cuda12.get("ready"):
            ready = False
            reasons.append("cuda12_pip_libs_missing")
    except Exception as exc:  # noqa: BLE001
        ready = False
        reasons.append(f"stt_build:{type(exc).__name__}:{exc}")
        report["stt_health"] = {"ok": False, "error": str(exc)}

    # Piper
    piper = _piper_voice(settings)
    report["piper"] = piper
    if not piper.get("ok"):
        ready = False
        reasons.append("piper_voice_missing")
    try:
        import asyncio

        from limen.voice.tts import build_tts_provider

        tts = build_tts_provider(settings)
        tts_health = asyncio.run(tts.health())  # type: ignore[misc]
        report["tts_health"] = tts_health
        if not tts_health.get("ok"):
            ready = False
            reasons.append(f"tts:{tts_health.get('error')}")
    except Exception as exc:  # noqa: BLE001
        ready = False
        reasons.append(f"tts_build:{type(exc).__name__}:{exc}")
        report["tts_health"] = {"ok": False, "error": str(exc)}

    # E5 embeddings (must not be stub)
    try:
        from limen.knowledge.embeddings import build_embedding_provider

        emb = build_embedding_provider(settings)
        if settings.embedding_provider.lower() == "stub":
            ready = False
            reasons.append("embedding_is_stub")
        # Light probe — encode a short string
        vectors = emb.embed_documents(["LIMEN challenge probe"])
        report["embedding_health"] = {
            "ok": True,
            "dimensions": getattr(emb, "dimensions", len(vectors[0]) if vectors else None),
            "provider": settings.embedding_provider,
        }
        if not vectors:
            ready = False
            reasons.append("embedding_empty")
    except Exception as exc:  # noqa: BLE001
        ready = False
        reasons.append(f"embedding:{type(exc).__name__}:{exc}")
        report["embedding_health"] = {"ok": False, "error": str(exc)}

    # Qdrant local path — exclusive lock is OK if another LIMEN process already holds it.
    try:
        from limen.knowledge.embeddings import build_embedding_provider
        from limen.knowledge.vector_store import get_vector_store, reset_vector_store_for_tests

        emb = build_embedding_provider(settings)
        store = get_vector_store(settings, dimensions=emb.dimensions)
        report["qdrant"] = {"ok": True, "backend": type(store).__name__}
        reset_vector_store_for_tests()
    except Exception as exc:  # noqa: BLE001
        msg = str(exc)
        lock_path = Path(settings.vector_path) / ".lock"
        if "already accessed" in msg.lower() and lock_path.exists():
            report["qdrant"] = {
                "ok": True,
                "note": "exclusive_lock_held_by_running_limen",
                "path": str(settings.vector_path),
            }
        else:
            ready = False
            reasons.append(f"qdrant:{type(exc).__name__}:{exc}")
            report["qdrant"] = {"ok": False, "error": str(exc)}

    node = _node_ok()
    report["frontend"] = node
    if not node.get("ok"):
        ready = False
        reasons.append("frontend_deps_missing")

    report["reasons"] = reasons
    report["READY_FOR_CHALLENGE_RUNTIME"] = bool(ready)
    print(json.dumps(report, indent=2, default=str))
    print(f"READY_FOR_CHALLENGE_RUNTIME={'TRUE' if ready else 'FALSE'}")
    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
