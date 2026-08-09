#!/usr/bin/env python3
"""Real voice benchmark: WAV → STT → CallService → TTS. Writes generated report."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import uuid
from datetime import datetime as dt

from limen.auth.models import StoredAccount
from limen.config.settings import ApplicationSettings
from limen.conversation.call_service import CallService
from limen.intelligence.providers.factory import build_llm_provider
from limen.persistence.database import Database
from limen.persistence.repositories.accounts import SqliteAccountRepository
from limen.persistence.repositories.calls import SqliteCallRepository
from limen.persistence.repositories.traces import SqliteTraceRepository
from limen.safety.decision import Severity
from limen.telemetry.percentiles import percentile
from limen.voice.audio_codec import wav_duration_ms
from limen.voice.stt import build_stt_provider
from limen.voice.tts import build_tts_provider

FIXTURES = ROOT / "tests" / "fixtures" / "voice"

SCENARIOS: list[dict[str, Any]] = [
    {
        "id": "clean_air",
        "wav": "es_clean_air.wav",
        "expect_tokens": ["falta", "aire"],
        "risk_hint": "RED_or_ORANGE",
    },
    {
        "id": "red_breath",
        "wav": "es_red_breath.wav",
        "expect_tokens": ["respirar"],
        "expect_escalate": True,
        "risk_hint": "RED",
    },
    {
        "id": "green_ok",
        "wav": "es_green_ok.wav",
        "expect_tokens": ["bien"],
        "expect_escalate": False,
        "risk_hint": "GREEN_like",
    },
    {"id": "col_aire", "wav": "es_col_aire.wav", "expect_tokens": ["aire"]},
    {
        "id": "col_aguita",
        "wav": "es_col_aguita.wav",
        "expect_tokens": ["aguita", "agüita", "agua", "abuita"],
    },
    {"id": "col_arde", "wav": "es_col_arde.wav", "expect_tokens": ["arde"]},
    {"id": "col_abrio", "wav": "es_col_abrio.wav", "expect_tokens": ["abri"]},
    {"id": "col_vuelto", "wav": "es_col_vuelto.wav", "expect_tokens": ["vuelto", "nada"]},
    {
        "id": "negation",
        "wav": "es_negation.wav",
        "expect_tokens": ["no"],
        "preserve_negation": True,
    },
    {"id": "numbers", "wav": "es_numbers.wav", "expect_tokens": ["temperatura", "dos"]},
    {"id": "meds", "wav": "es_meds.wav", "expect_tokens": ["acetamin"]},
    {"id": "noise_bg", "wav": "es_noise_bg.wav", "expect_tokens": ["aire"]},
    {"id": "low_volume", "wav": "es_low_volume.wav", "expect_tokens": ["aire"]},
    {"id": "pause_heavy", "wav": "es_pause_heavy.wav", "expect_tokens": ["aire"]},
]


def _gpu_snapshot() -> dict[str, Any]:
    try:
        proc = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,memory.used,utilization.gpu",
                "--format=csv,noheader,nounits",
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if proc.returncode != 0:
            return {"status": "UNMEASURED", "error": proc.stderr.strip()}
        line = proc.stdout.strip().splitlines()[0]
        parts = [p.strip() for p in line.split(",")]
        return {
            "status": "measured",
            "name": parts[0],
            "vram_total_mib": float(parts[1]),
            "vram_used_mib": float(parts[2]),
            "util_pct": float(parts[3]) if len(parts) > 3 else None,
        }
    except Exception as exc:  # noqa: BLE001
        return {"status": "UNMEASURED", "error": f"{type(exc).__name__}:{exc}"}


def _token_hit(text: str, tokens: list[str]) -> bool:
    lowered = text.casefold()
    return any(tok.casefold() in lowered for tok in tokens)


async def _run_one(
    *,
    scenario: dict[str, Any],
    stt: Any,
    tts: Any,
    service: CallService,
    account_id: str,
    voice: str,
    warm: bool,
) -> dict[str, Any]:
    from limen.voice.timing_record import VoiceTurnTimingRecord

    wav_path = FIXTURES / str(scenario["wav"])
    audio = wav_path.read_bytes()
    created = service.create(account_id=account_id, patient_alias="bench-voice")
    call_id = created["call_id"]

    # Same-clock record: speech_end BEFORE STT (fixture has no mic clock).
    speech_end = time.perf_counter()
    record = VoiceTurnTimingRecord(
        sample_id=f"{call_id}:{scenario['id']}",
        turn_id=scenario["id"],
        speech_end=speech_end,
    )
    record.stt_start = time.perf_counter()
    transcript = await stt.transcribe(audio, language="es")
    record.stt_end = time.perf_counter()

    record.turn_processing_start = time.perf_counter()
    result = await service.process_text_turn(
        account_id=account_id,
        call_id=call_id,
        user_text=transcript.normalized_text or transcript.text,
    )
    record.turn_processing_end = time.perf_counter()
    assert result is not None
    llm_lat = result.metrics.get("llm_latency_ms")
    if isinstance(llm_lat, (int, float)) and llm_lat > 0:
        record.llm_end = record.turn_processing_end
        record.llm_start = record.turn_processing_end - (float(llm_lat) / 1000.0)

    record.tts_start = time.perf_counter()
    speech = await tts.synthesize(result.assistant_text, voice)
    record.tts_ready = time.perf_counter()
    # No browser playback in fixture bench — challenge E2E stays None.
    record.validate_invariants()

    text = transcript.normalized_text or transcript.text or ""
    tokens = list(scenario.get("expect_tokens") or [])
    semantic_ok = _token_hit(text, tokens) if tokens else bool(text.strip())
    expect_esc = scenario.get("expect_escalate")
    escalate_ok = True
    if expect_esc is True:
        escalate_ok = bool(result.safety.escalate) and result.safety.severity >= Severity.ORANGE
    elif expect_esc is False:
        escalate_ok = not bool(result.safety.escalate)

    duration = wav_duration_ms(speech.audio) or speech.duration_ms or 0.0
    return {
        "id": scenario["id"],
        "warm": warm,
        "wav": scenario["wav"],
        "transcript": text,
        "semantic_ok": semantic_ok,
        "assistant_text": result.assistant_text,
        "severity": result.safety.severity.name,
        "escalate": bool(result.safety.escalate),
        "escalate_ok": escalate_ok,
        "timing_valid": record.valid,
        "invalid_reasons": list(record.invalid_reasons),
        "stt_ms": record.stt_ms,
        "turn_processing_ms": record.turn_processing_ms,
        "clinical_ms": result.metrics.get("clinical_ms"),
        "llm_ms": record.llm_ms
        or result.metrics.get("llm_latency_ms")
        or result.metrics.get("llm_generation_ms"),
        "rag_ms": result.metrics.get("retrieval_ms") or result.metrics.get("rag_ms"),
        "safety_ms": result.metrics.get("safety_ms"),
        "tts_ms": record.tts_ms,
        "SERVER_TTS_READY_PROXY_ms": record.server_tts_ready_proxy_ms,
        "challenge_voice_e2e_ms": record.challenge_voice_e2e_ms,
        "tts_duration_ms": duration,
        "tts_bytes": len(speech.audio),
        "valid_wav": speech.audio[:4] == b"RIFF" and duration > 0,
        "stt_device": (transcript.usage_metadata or {}).get("actual_device")
        or (transcript.usage_metadata or {}).get("device"),
        "stt_compute_type": (transcript.usage_metadata or {}).get("compute_type"),
        "metrics": dict(result.metrics),
        "timing_marks": record.to_metrics()["marks"],
    }


async def run_benchmark(*, repeats: int, out_dir: Path) -> dict[str, Any]:
    settings = ApplicationSettings(
        STT_PROVIDER=os.environ.get("STT_PROVIDER", "faster_whisper"),
        STT_MODEL=os.environ.get("STT_MODEL", "Systran/faster-whisper-small"),
        STT_DEVICE=os.environ.get("STT_DEVICE", "cuda"),
        STT_COMPUTE_TYPE=os.environ.get("STT_COMPUTE_TYPE", "default"),
        TTS_PROVIDER=os.environ.get("TTS_PROVIDER", "piper"),
        TTS_VOICE=os.environ.get("TTS_VOICE", "es_MX-claude-high"),
        TTS_MODEL_PATH=os.environ.get("TTS_MODEL_PATH", str(ROOT / "runtime" / "models" / "piper")),
        LLM_PROVIDER=os.environ.get("LLM_PROVIDER", "ollama"),
        LLM_MODEL=os.environ.get("LLM_MODEL", "phi3.5"),
        EMBEDDING_PROVIDER=os.environ.get("EMBEDDING_PROVIDER", "stub"),
        _env_file=None,
    )
    stt = build_stt_provider(settings)
    tts = build_tts_provider(settings)
    llm = build_llm_provider(settings)

    vram_baseline = _gpu_snapshot()
    await stt.health()  # type: ignore[misc]
    vram_after_stt = _gpu_snapshot()
    await tts.health()  # type: ignore[misc]

    db_path = out_dir / "bench.sqlite3"
    database = Database(db_path)
    database.initialize()
    accounts = SqliteAccountRepository(database)
    account = StoredAccount(
        account_id=str(uuid.uuid4()),
        email=f"voice-bench-{out_dir.name}@limen.local",
        display_name="Voice Bench",
        created_at=dt.now(tz=UTC),
        password_hash="x",
    )
    accounts.insert_account(account)
    calls = SqliteCallRepository(database)
    traces = SqliteTraceRepository(database)
    service = CallService(calls, traces, llm=llm)

    # Cold first load already happened in health(); still mark first scenario cold.
    samples: list[dict[str, Any]] = []
    first = True
    for _ in range(max(1, repeats)):
        for scenario in SCENARIOS:
            if not (FIXTURES / scenario["wav"]).is_file():
                samples.append({"id": scenario["id"], "error": "fixture_missing"})
                continue
            row = await _run_one(
                scenario=scenario,
                stt=stt,
                tts=tts,
                service=service,
                account_id=account.account_id,
                voice=settings.tts_voice,
                warm=not first,
            )
            samples.append(row)
            first = False

    vram_combined = _gpu_snapshot()
    warm = [
        s
        for s in samples
        if s.get("warm")
        and s.get("valid_wav")
        and s.get("semantic_ok")
        and s.get("timing_valid", True)
    ]
    proxy = [
        float(s["SERVER_TTS_READY_PROXY_ms"])
        for s in warm
        if s.get("SERVER_TTS_READY_PROXY_ms") is not None
    ]
    stt_l = [float(s["stt_ms"]) for s in warm if s.get("stt_ms") is not None]
    turn_l = [
        float(s["turn_processing_ms"]) for s in warm if s.get("turn_processing_ms") is not None
    ]
    tts_l = [float(s["tts_ms"]) for s in warm if s.get("tts_ms") is not None]
    llm_l = [float(s["llm_ms"]) for s in warm if s.get("llm_ms") is not None]
    safety_l = [float(s["safety_ms"]) for s in warm if s.get("safety_ms") is not None]
    rag_l = [float(s["rag_ms"]) for s in warm if s.get("rag_ms") is not None]

    cold = next((s for s in samples if not s.get("warm") and "stt_ms" in s), None)
    summary = {
        "timestamp": datetime.now(tz=UTC).isoformat(),
        "environment": {
            "python": sys.version.split()[0],
            "stt_provider": settings.stt_provider,
            "stt_model": settings.stt_model,
            "stt_device": settings.stt_device,
            "tts_provider": settings.tts_provider,
            "tts_voice": settings.tts_voice,
            "llm_provider": settings.llm_provider,
            "llm_model": settings.llm_model,
            "embedding_provider": settings.embedding_provider,
        },
        "vram": {
            "baseline": vram_baseline,
            "after_stt_load": vram_after_stt,
            "combined_runtime": vram_combined,
            "note": (
                "Host nvidia-smi snapshots. STT placement must come from "
                "actual_device in STT health, not from VRAM alone."
            ),
        },
        "sample_count_warm_ok": len(warm),
        "sample_count_total": len(samples),
        "cold_first_turn": {
            "SERVER_TTS_READY_PROXY_ms": cold.get("SERVER_TTS_READY_PROXY_ms") if cold else None,
            "stt_ms": cold.get("stt_ms") if cold else None,
            "id": cold.get("id") if cold else None,
        },
        "warm_metrics": {
            "SERVER_TTS_READY_PROXY_p50_ms": percentile(proxy, 50) if proxy else None,
            "SERVER_TTS_READY_PROXY_p95_ms": percentile(proxy, 95) if proxy else None,
            "stt_p50_ms": percentile(stt_l, 50) if stt_l else None,
            "turn_processing_p50_ms": percentile(turn_l, 50) if turn_l else None,
            "tts_p50_ms": percentile(tts_l, 50) if tts_l else None,
            "llm_p50_ms": percentile(llm_l, 50) if llm_l else None,
            "safety_p50_ms": percentile(safety_l, 50) if safety_l else None,
            "rag_p50_ms": percentile(rag_l, 50) if rag_l else None,
            "challenge_voice_e2e_p50_ms": None,
            "challenge_voice_e2e_p95_ms": None,
            "boundary_note": (
                "SERVER_TTS_READY_PROXY = speech_end→tts_ready (server fixture). "
                "NOT challenge_voice_latency. Official P50/P95 require browser "
                "playback-start samples."
            ),
        },
        "samples": samples,
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    return summary


def write_docs(summary: dict[str, Any], docs_path: Path) -> None:
    warm = summary.get("warm_metrics") or {}
    env = summary.get("environment") or {}
    cold = summary.get("cold_first_turn") or {}
    lines = [
        "# LIMEN Voice Benchmark (generated)",
        "",
        f"Generated: `{summary.get('timestamp')}`",
        "",
        "## Environment",
        "",
        f"- STT: `{env.get('stt_provider')}` / `{env.get('stt_model')}` "
        f"(device config `{env.get('stt_device')}`)",
        f"- TTS: `{env.get('tts_provider')}` / `{env.get('tts_voice')}`",
        f"- LLM: `{env.get('llm_provider')}` / `{env.get('llm_model')}`",
        f"- Embeddings: `{env.get('embedding_provider')}`",
        "",
        "## Sample counts",
        "",
        f"- Total rows: **{summary.get('sample_count_total')}**",
        f"- Warm OK (timing-valid): **{summary.get('sample_count_warm_ok')}**",
        "",
        "## SERVER_TTS_READY_PROXY (not challenge latency)",
        "",
        f"- Cold first-turn proxy: **{cold.get('SERVER_TTS_READY_PROXY_ms')}** ms "
        f"(`{cold.get('id')}`)",
        f"- Warm proxy P50: **{warm.get('SERVER_TTS_READY_PROXY_p50_ms')}** ms",
        f"- Warm proxy P95: **{warm.get('SERVER_TTS_READY_PROXY_p95_ms')}** ms",
        "",
        "## Official challenge voice latency (browser playback-start)",
        "",
        f"- P50: **{warm.get('challenge_voice_e2e_p50_ms')}**",
        f"- P95: **{warm.get('challenge_voice_e2e_p95_ms')}**",
        "",
        "## Same-sample stage P50 (warm OK)",
        "",
        f"- STT P50: **{warm.get('stt_p50_ms')}** ms",
        f"- turn_processing P50: **{warm.get('turn_processing_p50_ms')}** ms",
        f"- LLM P50: **{warm.get('llm_p50_ms')}** ms",
        f"- TTS P50: **{warm.get('tts_p50_ms')}** ms",
        f"- Safety P50: **{warm.get('safety_p50_ms')}** ms",
        f"- RAG P50: **{warm.get('rag_p50_ms')}** ms",
        "",
        "## Boundary honesty",
        "",
        str(warm.get("boundary_note") or ""),
        "",
        "## Stage semantics",
        "",
        "- `clinical_ms` (orchestrator): clinical extraction stage only.",
        "- `turn_processing_ms`: STT-end → TTS-start wall (core LIMEN path).",
        "- Do not add independent stage P50s to reconstruct E2E P50.",
        "",
        "## VRAM snapshots",
        "",
        "```json",
        json.dumps(summary.get("vram"), indent=2, ensure_ascii=False),
        "```",
        "",
    ]
    docs_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=2, help="Scenario set repeats")
    parser.add_argument("--write-docs", action="store_true")
    parser.add_argument(
        "--run-dir",
        default="",
        help="Output directory (default runtime/benchmarks/voice/<ts>)",
    )
    args = parser.parse_args()
    ts = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
    out_dir = Path(args.run_dir) if args.run_dir else ROOT / "runtime" / "benchmarks" / "voice" / ts
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = asyncio.run(run_benchmark(repeats=args.repeats, out_dir=out_dir))
    if args.write_docs:
        write_docs(summary, ROOT / "docs" / "VOICE_BENCHMARK.generated.md")
    payload = {"out_dir": str(out_dir)}
    payload.update({k: summary[k] for k in summary if k != "samples"})
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
