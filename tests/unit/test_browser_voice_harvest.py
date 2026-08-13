"""Official browser E2E harvest ignores cross-clock tts_ready vs playback."""

from __future__ import annotations

import json

from limen.conversation.call_service import _merge_voice_latency_samples
from limen.telemetry.browser_voice import (
    aggregate_challenge_voice,
    parse_playback_sample,
)


def test_cross_clock_reason_still_official() -> None:
    sample = parse_playback_sample(
        call_id="c1",
        sequence=4,
        metrics_json=json.dumps(
            {
                "challenge_voice_e2e_ms": 6457.0,
                "valid": False,
                "invalid_reasons": ["tts_ready>audio_playback_start"],
            }
        ),
        payload_json="{}",
    )
    assert sample is not None
    assert sample.official
    assert sample.e2e_ms == 6457.0


def test_blocking_reason_rejects_sample() -> None:
    sample = parse_playback_sample(
        call_id="c1",
        sequence=4,
        metrics_json=json.dumps(
            {
                "challenge_voice_e2e_ms": 100.0,
                "invalid_reasons": ["challenge_e2e_ms<stt_ms"],
            }
        ),
        payload_json="{}",
    )
    assert sample is not None
    assert not sample.official


def test_warm_percentiles_exclude_first_playback_per_call() -> None:
    samples = []
    for seq, e2e in enumerate([8000.0, 4000.0, 5000.0], start=1):
        parsed = parse_playback_sample(
            call_id="call-a",
            sequence=seq,
            metrics_json=json.dumps({"challenge_voice_e2e_ms": e2e}),
            payload_json="{}",
        )
        assert parsed is not None
        samples.append(parsed)
    other = parse_playback_sample(
        call_id="call-b",
        sequence=1,
        metrics_json=json.dumps({"challenge_voice_e2e_ms": 9000.0}),
        payload_json="{}",
    )
    assert other is not None
    samples.append(other)
    agg = aggregate_challenge_voice(samples)
    assert agg["cold_n"] == 2
    assert agg["warm_n"] == 2
    assert agg["warm_p50_ms"] == 4000.0
    assert agg["status"] == "insufficient_samples"


def test_merge_keeps_longer_latency_list() -> None:
    prior = {"voice_latencies_ms": [100.0]}
    fresh = {"voice_latencies_ms": [100.0, 200.0]}
    assert _merge_voice_latency_samples(prior, fresh) == [100.0, 200.0]
    assert _merge_voice_latency_samples(fresh, prior) == [100.0, 200.0]
