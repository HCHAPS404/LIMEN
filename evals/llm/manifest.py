"""Benchmark manifest — machine-readable run identity (no secrets)."""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from evals.llm.preflight import (
    G3_LOCAL_CANDIDATES,
    collect_hardware,
    default_base_url,
    detect_nvidia_gpu,
)

ROOT = Path(__file__).resolve().parents[2]

BENCHMARK_VERSION = "5C.2.1"
SAFETY_POLICY_VERSION = "phase4-frozen"  # production Safety Governor not modified in 5C
RAG_CONFIG_ID = "hybrid-e5-rrf-phase3.2-frozen"


def git_sha() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def build_manifest(
    *,
    temperature: float,
    max_tokens: int,
    repeats: int,
    case_ids: list[str],
    dataset_sources: list[str],
    ollama_version: str | None,
    candidate_models: list[str] | None = None,
    base_url: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    hw = collect_hardware()
    gpu_detail = detect_nvidia_gpu()
    manifest: dict[str, Any] = {
        "benchmark_version": BENCHMARK_VERSION,
        "commit_sha": git_sha(),
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "os": hw.get("os"),
        "kernel": hw.get("kernel"),
        "cpu": hw.get("cpu"),
        "ram_bytes": hw.get("ram_bytes"),
        "gpu": hw.get("gpu", "UNMEASURED"),
        "gpu_name": gpu_detail.get("name", "UNMEASURED"),
        "gpu_vram_bytes": gpu_detail.get("vram_bytes", "UNMEASURED"),
        "python_version": hw.get("python") or platform.python_version(),
        "ollama_version": ollama_version if ollama_version else "UNMEASURED",
        "LLM_BASE_URL": base_url or default_base_url(),
        "candidate_models": list(candidate_models or G3_LOCAL_CANDIDATES),
        "temperature": temperature,
        "max_tokens": max_tokens,
        "repeat_count": repeats,
        "benchmark_cases": case_ids,
        "dataset_sources": dataset_sources,
        "rag_configuration_id": RAG_CONFIG_ID,
        "safety_policy_version": SAFETY_POLICY_VERSION,
        "notes": [
            "PHASE 5C orchestration only; production LLM default unchanged.",
            "Advisory risk predictions are BENCHMARK ONLY.",
            "No API keys or patient identifying data included.",
        ],
    }
    if extra:
        manifest.update(extra)
    return manifest


def manifest_fingerprint(manifest: dict[str, Any]) -> str:
    """Stable hash for resume eligibility (excludes generated_at)."""
    clone = {k: v for k, v in manifest.items() if k != "generated_at"}
    payload = json.dumps(clone, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def manifests_compatible(a: dict[str, Any], b: dict[str, Any]) -> bool:
    keys = (
        "benchmark_version",
        "commit_sha",
        "temperature",
        "max_tokens",
        "repeat_count",
        "benchmark_cases",
        "dataset_sources",
        "rag_configuration_id",
        "safety_policy_version",
        "LLM_BASE_URL",
        "candidate_models",
    )
    return all(a.get(key) == b.get(key) for key in keys)
