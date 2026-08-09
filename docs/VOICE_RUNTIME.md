# LIMEN Voice Runtime — PHASE 6

Human-maintained. Metrics must come from generated runs, not estimates.

## Architecture

Voice wraps the frozen text-turn pipeline:

```text
Browser mic → VAD endpoint → WAV PCM16 mono 16 kHz
  → WebSocket /api/calls/{id}/stream
  → STT (faster-whisper | stub)
  → CallService.process_text_turn  (unchanged clinical core)
  → validated assistant_text
  → TTS (piper | stub)
  → browser playback
```

Safety Governor, enforce_floor, ClinicalState, Hybrid RAG, and Phi safety
boundary are **unchanged**. STT/TTS never decide clinical risk.

## Providers

| Role | Challenge runtime | CI default |
| --- | --- | --- |
| STT | `faster_whisper` / `Systran/faster-whisper-small` | `stub` |
| TTS | `piper` / `es_MX-claude-high` | `stub` |

Install / prepare (canonical `.venv` only):

```bash
make prepare-voice
# = pip install -e '.[voice]'  (includes nvidia-cublas-cu12 + nvidia-cudnn-cu12)
# + download Piper es_MX-claude-high under runtime/models/piper/
# + load/cache Systran/faster-whisper-small
# + generate tests/fixtures/voice/*.wav via Piper (no private recordings)

make verify-voice-environment   # READY_FOR_REAL_VOICE=TRUE/FALSE (STT_DEVICE=cuda)
make verify-voice               # stub path (CI)
make verify-voice-real          # real STT/TTS + fixture bench
make dev-api-voice              # uvicorn with CUDA12 LD_LIBRARY_PATH
```

CUDA note: system driver may be CUDA 13; CTranslate2 needs CUDA **12** user libs.
LIMEN resolves them from pip packages via `limen.voice.cuda_runtime` — no driver downgrade,
no `/usr` SONAME fakes. With `STT_DEVICE=cuda`, health exposes `configured_device` /
`actual_device` / `fallback_reason` and does not claim healthy success on silent CPU.

Piper voice license: MIT via `rhasspy/piper-voices` (see `runtime/models/piper/LICENSE_NOTE.txt`).
Do not commit `*.onnx` weights.

## Audio format

- **Input (canonical):** WAV, PCM 16-bit, mono, 16 kHz (browser encodes; no FFmpeg).
- **TTS output:** WAV PCM (stub silent WAV; Piper native rate wrapped as WAV).
- Raw audio is transient (`runtime/tmp/voice/`); transcripts + timings persist.

## Endpointing / barge-in (PHASE 6.3 measured defaults)

Prefer natural turn-taking over minimum latency (pause-heavy Spanish).

| Knob | Default | Approx. time (`poll=60ms`) |
| --- | --- | --- |
| `speechFrames` | 4 | ~240 ms to open speech |
| `silenceFrames` | 28 | ~1680 ms silence to end turn |
| `speechThreshold` / `silenceThreshold` | 0.045 / 0.02 | hysteresis |
| `minUtteranceMs` / `maxUtteranceMs` | 320 / 45000 | discard / hard cap |
| `bargeInSpeechFrames` | 8 | ~480 ms sustained speech while SPEAKING |

- getUserMedia requests `echoCancellation`, `noiseSuppression`, `autoGainControl` when supported.
- Barge-in: require sustained speech (not a spike) → stop playback → `voice.interrupt` → discard stale TTS by `turn_seq`.
- Interrupted assistant intent + pending question persist in `conversation_context` (metrics blob).
- SafetyDecision from completed turns remains persisted even if audio was cancelled.

## Latency challenge boundary

`voice_response_latency_ms` = client `speech_end_monotonic` → client
`agent_audio_started_monotonic` (first audible playback).

Aggregates:

- `< 3` samples → `insufficient_samples`
- `≥ 3` → `measured` P50/P95
- none → `not_implemented`

Text-turn LLM latency remains a separate metric.

## Configuration

```bash
# CI / deterministic
STT_PROVIDER=stub
TTS_PROVIDER=stub

# Challenge voice (opt-in)
# STT_PROVIDER=faster_whisper
# STT_MODEL=Systran/faster-whisper-small
# STT_DEVICE=auto
# TTS_PROVIDER=piper
# TTS_VOICE=es_MX-claude-high
# TTS_MODEL_PATH=./runtime/models/piper
```

## Degraded modes

| Failure | Behavior |
| --- | --- |
| STT fail | Observable error, retry, no invented transcript; text turn still available |
| TTS fail | Assistant text remains; conversation continues |
| LLM fail | Deterministic templates (PHASE 5.1) |
| Mic denied | Recoverable ERROR state |

## Tests

- Unit: codec, VAD endpointing, latency math, stale-turn helpers
- Integration: WS binary stub STT→pipeline→stub WAV TTS
- `real_voice` opt-in: `LIMEN_REAL_VOICE=1`

## Manual browser check (G4)

Requires real providers (`STT_PROVIDER=faster_whisper`, `TTS_PROVIDER=piper`), not stubs.

1. Sign in → Call → allow microphone
2. Speak Spanish → hear Piper response
3. Second turn works
4. Interrupt while speaking → playback stops; stale `turn_seq` discarded
5. End call → summary/TRAZA

Record result as `G4_MANUAL_SMOKE=PASS/FAIL` in the voice benchmark notes.

## Known debt

- Browser capture still uses `ScriptProcessorNode` (deprecated).
  **AudioWorklet migration = post-challenge / future hardening.**
  Do not block G4 on AudioWorklet.
