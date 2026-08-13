"""Harvest official browser voice E2E samples from TRAZA events.

Challenge boundary: patient speech_end → browser audio_playback_start
(same client monotonic clock). Server ``tts_ready`` lives on a different
clock and must not veto an otherwise valid E2E sample.
"""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from limen.telemetry.percentiles import p50, p95

CROSS_CLOCK_INVARIANT_REASONS = frozenset({"tts_ready>audio_playback_start"})


@dataclass(frozen=True)
class BrowserVoiceSample:
    call_id: str
    sequence: int
    e2e_ms: float
    official: bool
    blocking_reasons: tuple[str, ...]


def blocking_e2e_reasons(reasons: list[str] | tuple[str, ...] | None) -> tuple[str, ...]:
    return tuple(
        str(reason)
        for reason in (reasons or [])
        if str(reason) not in CROSS_CLOCK_INVARIANT_REASONS
    )


def parse_playback_sample(
    *,
    call_id: str,
    sequence: int,
    metrics_json: str | None,
    payload_json: str | None,
) -> BrowserVoiceSample | None:
    try:
        metrics = json.loads(metrics_json or "{}")
    except json.JSONDecodeError:
        metrics = {}
    try:
        payload = json.loads(payload_json or "{}")
    except json.JSONDecodeError:
        payload = {}
    if not isinstance(metrics, dict):
        metrics = {}
    if not isinstance(payload, dict):
        payload = {}
    raw = metrics.get("challenge_voice_e2e_ms")
    if raw is None:
        raw = metrics.get("voice_response_latency_ms")
    try:
        e2e_ms = float(raw)
    except (TypeError, ValueError):
        return None
    if e2e_ms < 0:
        return None
    reasons = metrics.get("invalid_reasons") or payload.get("invalid_reasons") or []
    if not isinstance(reasons, list):
        reasons = []
    blocking = blocking_e2e_reasons([str(item) for item in reasons])
    return BrowserVoiceSample(
        call_id=call_id,
        sequence=int(sequence),
        e2e_ms=e2e_ms,
        official=not blocking,
        blocking_reasons=blocking,
    )


def harvest_playback_samples(connection: Any) -> list[BrowserVoiceSample]:
    rows = connection.execute(
        """
        SELECT call_id, sequence, metrics_json, payload_json
        FROM trace_events
        WHERE event_type = 'voice.playback.started'
        ORDER BY call_id, sequence
        """
    ).fetchall()
    samples: list[BrowserVoiceSample] = []
    for row in rows:
        sample = parse_playback_sample(
            call_id=str(row["call_id"]),
            sequence=int(row["sequence"]),
            metrics_json=row["metrics_json"],
            payload_json=row["payload_json"],
        )
        if sample is not None:
            samples.append(sample)
    return samples


def aggregate_challenge_voice(samples: Sequence[BrowserVoiceSample]) -> dict[str, Any]:
    official = [sample for sample in samples if sample.official]
    by_call: dict[str, list[BrowserVoiceSample]] = defaultdict(list)
    for sample in official:
        by_call[sample.call_id].append(sample)

    cold: list[float] = []
    warm: list[float] = []
    for recs in by_call.values():
        ordered = sorted(recs, key=lambda item: item.sequence)
        for index, sample in enumerate(ordered):
            if index == 0:
                cold.append(sample.e2e_ms)
            else:
                warm.append(sample.e2e_ms)

    all_ms = [sample.e2e_ms for sample in official]
    return {
        "source": "traza_voice.playback.started",
        "boundary": "client_speech_end_monotonic → client_audio_playback_start_monotonic",
        "excluded_cross_clock_reasons": sorted(CROSS_CLOCK_INVARIANT_REASONS),
        "playback_events": len(samples),
        "official_n": len(official),
        "rejected_n": len(samples) - len(official),
        "calls_with_playback": len(by_call),
        "cold_n": len(cold),
        "cold_ms": _round_ms(p50(cold)),
        "cold_p50_ms": _round_ms(p50(cold)),
        "warm_n": len(warm),
        "warm_p50_ms": _round_ms(p50(warm)),
        "warm_p95_ms": _round_ms(p95(warm)),
        "all_official_p50_ms": _round_ms(p50(all_ms)),
        "all_official_p95_ms": _round_ms(p95(all_ms)),
        "status": _status(len(warm)),
        "methodology": (
            "Warm samples exclude the first playback.started per call_id. "
            "Percentiles: nearest-rank ceil(p/100 * n). "
            "tts_ready vs audio_playback_start is a cross-clock comparison and "
            "does not exclude official E2E."
        ),
    }


def _round_ms(value: float | None) -> float | None:
    if value is None:
        return None
    return round(float(value), 1)


def _status(warm_n: int) -> str:
    if warm_n >= 20:
        return "measured"
    if warm_n >= 3:
        return "insufficient_samples"
    if warm_n > 0:
        return "insufficient_samples"
    return "not_implemented"
