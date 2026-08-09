#!/usr/bin/env python3
"""Preflight for real voice runtime. Ends with READY_FOR_REAL_VOICE=TRUE/FALSE."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from limen.config.settings import ApplicationSettings
from limen.voice.cuda_runtime import ensure_cuda12_library_path
from limen.voice.stt import build_stt_provider
from limen.voice.tts import build_tts_provider


def _ollama_status(base: str) -> dict[str, object]:
    url = base.rstrip("/") + "/api/tags"
    try:
        with urllib.request.urlopen(url, timeout=3) as resp:  # noqa: S310
            payload = json.loads(resp.read().decode("utf-8"))
        names = [str(m.get("name") or "") for m in payload.get("models") or []]
        return {"reachable": True, "models": names}
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        return {"reachable": False, "error": f"{type(exc).__name__}:{exc}", "models": []}


def _cuda_status() -> dict[str, object]:
    out: dict[str, object] = {"nvidia_smi": False, "ctranslate2_cuda_count": 0}
    try:
        import subprocess

        proc = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,memory.used",
                "--format=csv,noheader",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            out["nvidia_smi"] = True
            out["gpu_line"] = proc.stdout.strip().splitlines()[0]
    except Exception as exc:  # noqa: BLE001
        out["nvidia_smi_error"] = f"{type(exc).__name__}:{exc}"
    # Ensure ensure runs before CT2 in subprocess-style import path
    try:
        import ctranslate2

        out["ctranslate2_cuda_count"] = int(ctranslate2.get_cuda_device_count())
    except Exception as exc:  # noqa: BLE001
        out["ctranslate2_error"] = f"{type(exc).__name__}:{exc}"
    return out


def main() -> int:
    cuda12 = ensure_cuda12_library_path()
    # Challenge voice defaults when operator opts into real voice verify.
    env_overrides = {
        "STT_PROVIDER": os.environ.get("STT_PROVIDER", "faster_whisper"),
        "STT_MODEL": os.environ.get("STT_MODEL", "Systran/faster-whisper-small"),
        "STT_DEVICE": os.environ.get("STT_DEVICE", "cuda"),
        "STT_COMPUTE_TYPE": os.environ.get("STT_COMPUTE_TYPE", "default"),
        "TTS_PROVIDER": os.environ.get("TTS_PROVIDER", "piper"),
        "TTS_VOICE": os.environ.get("TTS_VOICE", "es_MX-claude-high"),
        "TTS_MODEL_PATH": os.environ.get(
            "TTS_MODEL_PATH", str(ROOT / "runtime" / "models" / "piper")
        ),
    }
    settings = ApplicationSettings(**env_overrides, _env_file=None)

    report: dict[str, object] = {
        "python": sys.version.split()[0],
        "stt_provider_config": settings.stt_provider,
        "stt_model_config": settings.stt_model,
        "stt_device_config": settings.stt_device,
        "tts_provider_config": settings.tts_provider,
        "tts_voice_config": settings.tts_voice,
        "audio_format": "WAV PCM16 mono 16kHz (STT input); Piper native rate WAV (TTS)",
        "cuda": _cuda_status(),
        "cuda12_pip_libs": cuda12,
    }

    ready = True
    reasons: list[str] = []

    # STT
    try:
        stt = build_stt_provider(settings)
        import asyncio

        stt_health = asyncio.run(stt.health())  # type: ignore[misc]
        report["stt"] = stt_health
        if not stt_health.get("ok"):
            ready = False
            reasons.append(f"stt:{stt_health.get('error')}")
        if settings.stt_provider == "stub":
            ready = False
            reasons.append("stt_provider_is_stub")
        if settings.stt_device.lower() == "cuda" and stt_health.get("actual_device") != "cuda":
            ready = False
            reasons.append(
                f"stt_requested_cuda_actual_{stt_health.get('actual_device')}"
            )
        if not cuda12.get("ready"):
            ready = False
            reasons.append("cuda12_pip_libs_missing")
    except Exception as exc:  # noqa: BLE001
        ready = False
        reasons.append(f"stt_build:{type(exc).__name__}:{exc}")
        report["stt"] = {"ok": False, "error": str(exc)}

    # TTS
    try:
        tts = build_tts_provider(settings)
        import asyncio

        tts_health = asyncio.run(tts.health())  # type: ignore[misc]
        report["tts"] = tts_health
        if not tts_health.get("ok"):
            ready = False
            reasons.append(f"tts:{tts_health.get('error')}")
        if settings.tts_provider == "stub":
            ready = False
            reasons.append("tts_provider_is_stub")
        onnx = Path(str(tts_health.get("model_path") or ""))
        if not onnx.is_file():
            ready = False
            reasons.append("tts_onnx_missing")
    except Exception as exc:  # noqa: BLE001
        ready = False
        reasons.append(f"tts_build:{type(exc).__name__}:{exc}")
        report["tts"] = {"ok": False, "error": str(exc)}

    ollama_base = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    ollama = _ollama_status(ollama_base)
    report["ollama"] = ollama
    phi_ok = any("phi3.5" in n for n in (ollama.get("models") or []))  # type: ignore[operator]
    report["phi_available"] = phi_ok
    if not ollama.get("reachable"):
        ready = False
        reasons.append("ollama_unreachable")
    if not phi_ok:
        ready = False
        reasons.append("phi3.5_missing")

    emb_provider = os.environ.get("EMBEDDING_PROVIDER", "stub")
    report["embedding_provider"] = emb_provider
    report["embedding_status"] = (
        "configured_stub"
        if emb_provider == "stub"
        else "configured_non_stub_not_probed_here"
    )

    report["reasons"] = reasons
    report["READY_FOR_REAL_VOICE"] = ready

    print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
    print("---")
    print(f"STT_PROVIDER={settings.stt_provider}")
    print(f"STT_MODEL={settings.stt_model}")
    stt_block = report.get("stt") or {}
    print(f"STT_CONFIGURED_DEVICE={settings.stt_device}")
    print(f"STT_ACTUAL_DEVICE={stt_block.get('actual_device', 'UNMEASURED')}")
    print(f"STT_COMPUTE_TYPE={stt_block.get('compute_type', 'UNMEASURED')}")
    print(f"STT_FALLBACK={stt_block.get('fallback_reason')}")
    print(f"TTS_PROVIDER={settings.tts_provider}")
    print(f"TTS_VOICE={settings.tts_voice}")
    print(f"TTS_MODEL_PATH={(report.get('tts') or {}).get('model_path')}")
    print(f"OLLAMA_REACHABLE={bool(ollama.get('reachable'))}")
    print(f"PHI_AVAILABLE={phi_ok}")
    print(f"EMBEDDING_PROVIDER={emb_provider}")
    cuda = report["cuda"]
    print(f"CUDA_NVIDIA_SMI={cuda.get('nvidia_smi')}")
    print(f"CTRANSLATE2_CUDA_COUNT={cuda.get('ctranslate2_cuda_count')}")
    print(f"CUDA12_PIP_LIBS_READY={bool(cuda12.get('ready'))}")
    print(f"READY_FOR_REAL_VOICE={'TRUE' if ready else 'FALSE'}")
    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
