# LIMEN Voice Benchmark (generated)

Generated: `2026-08-09T01:47:14.789795+00:00`

## Environment

- STT: `faster_whisper` / `Systran/faster-whisper-small` (device config `cuda`)
- TTS: `piper` / `es_MX-claude-high`
- LLM: `ollama` / `phi3.5`
- Embeddings: `stub`

## Sample counts

- Total rows: **28**
- Warm OK (timing-valid): **27**

## SERVER_TTS_READY_PROXY (not challenge latency)

- Cold first-turn proxy: **2782.447866993607** ms (`clean_air`)
- Warm proxy P50: **2239.8889939941** ms
- Warm proxy P95: **3353.775620998931** ms

## Official challenge voice latency (browser playback-start)

- P50: **None**
- P95: **None**

## Same-sample stage P50 (warm OK)

- STT P50: **141.43973498721607** ms
- turn_processing P50: **684.0387359989109** ms
- LLM P50: **650.7162060006522** ms
- TTS P50: **1492.2902599937515** ms
- Safety P50: **0.050825998187065125** ms
- RAG P50: **0.0013629905879497528** ms

## Boundary honesty

SERVER_TTS_READY_PROXY = speech_end→tts_ready (server fixture). NOT challenge_voice_latency. Official P50/P95 require browser playback-start samples.

## Stage semantics

- `clinical_ms` (orchestrator): clinical extraction stage only.
- `turn_processing_ms`: STT-end → TTS-start wall (core LIMEN path).
- Do not add independent stage P50s to reconstruct E2E P50.

## VRAM snapshots

```json
{
  "baseline": {
    "status": "measured",
    "name": "NVIDIA GeForce RTX 3060 Ti",
    "vram_total_mib": 8192.0,
    "vram_used_mib": 5036.0,
    "util_pct": 11.0
  },
  "after_stt_load": {
    "status": "measured",
    "name": "NVIDIA GeForce RTX 3060 Ti",
    "vram_total_mib": 8192.0,
    "vram_used_mib": 5892.0,
    "util_pct": 2.0
  },
  "combined_runtime": {
    "status": "measured",
    "name": "NVIDIA GeForce RTX 3060 Ti",
    "vram_total_mib": 8192.0,
    "vram_used_mib": 5898.0,
    "util_pct": 1.0
  },
  "note": "Host nvidia-smi snapshots. STT placement must come from actual_device in STT health, not from VRAM alone."
}
```

## PHASE 6.2 notes

- STT actual_device: **cuda** / compute **float16** (selected over int8_float16 by measured warm latency).
- CUDA 12 libs via pip (`nvidia-cublas-cu12`, `nvidia-cudnn-cu12`); system CUDA 13 driver unchanged.
- Timing audit: prior E2E P50 < STT P50 was a **fixture timer bug** (`speech_end` marked after STT). Fixed; proxy now includes STT.
- Official browser challenge P50/P95: still **UNMEASURED** (G4 mic not executed in this run).
- README voice metrics: **not updated** (no browser samples).
