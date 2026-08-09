"""PHASE 5C performance / display metric helpers (TEXT LLM INFERENCE only)."""

from __future__ import annotations

from typing import Any

UNMEASURED = "UNMEASURED"
NOT_AVAILABLE = "NOT_AVAILABLE"
NOT_IMPLEMENTED = "NOT_IMPLEMENTED"


def display(value: Any, *, missing: str = UNMEASURED) -> Any:
    """Human-facing render: never expose Python None."""
    if value is None:
        return missing
    return value


def tokens_per_second_ollama(
    *,
    completion_tokens: int | None,
    eval_duration_ns: int | float | None,
) -> float | None:
    """Ollama-native tok/s = eval_count / (eval_duration_ns / 1e9).

    Returns None when Ollama omits either field (caller → UNMEASURED).
    Never estimates from wall-clock or word counts.
    """
    if completion_tokens is None or eval_duration_ns is None:
        return None
    if completion_tokens <= 0:
        return None
    seconds = float(eval_duration_ns) / 1e9
    if seconds <= 0:
        return None
    return completion_tokens / seconds


def aggregate_tokens_per_second(rates: list[float]) -> float | None:
    if not rates:
        return None
    return sum(rates) / len(rates)


def cold_load_ms_from_usage(usage_metadata: dict[str, Any] | None, wall_ms: float) -> float:
    """Prefer Ollama load_duration_ns; else wall clock of first post-unload call."""
    if usage_metadata and usage_metadata.get("load_duration_ns") is not None:
        return float(usage_metadata["load_duration_ns"]) / 1e6
    return wall_ms


def classify_placement(*, size_vram: int | None, size_total: int | None) -> str:
    """Classify Ollama /api/ps residency without inventing GPU use."""
    if size_vram is None:
        return UNMEASURED
    if size_vram > 0:
        return "GPU"
    if size_total is not None and size_total > 0 and size_vram == 0:
        return "CPU"
    if size_vram == 0:
        return "CPU"
    return UNMEASURED
