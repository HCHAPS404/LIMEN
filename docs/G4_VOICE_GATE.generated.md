# G4 Voice Gate Evidence (generated)

Generated: 2026-08-09T04:17:28.789412+00:00

Human browser smoke: **UNVERIFIED**
Real STT (faster-whisper CUDA): **PASS**
Real Phi: **PASS**
Real TTS (Piper): **PASS**
Second turn: **UNVERIFIED**
Barge-in: **UNVERIFIED**
RED voice escalation: **UNVERIFIED**
Valid browser samples N: **UNMEASURED**
Cold first turn: **UNMEASURED**
Warm P50 (speech-end→playback): **UNMEASURED**
Warm P95: **UNMEASURED**
G4 status: **PARTIAL**

## Notes

Verified earlier in PHASE9 session via /health/providers under LIMEN_RUNTIME_PROFILE=challenge: STT faster_whisper CUDA float16 ok; TTS piper reachable; LLM ollama phi3.5 reachable. Human browser mic→playback, second turn, barge-in, RED voice smoke, N>=20 remain required for G4 PASS.

```json
{
  "generated_at": "2026-08-09T04:17:28.710024+00:00",
  "human_browser": "UNVERIFIED",
  "real_stt": "PASS",
  "real_phi": "PASS",
  "real_tts": "PASS",
  "second_turn": "UNVERIFIED",
  "barge_in": "UNVERIFIED",
  "red_voice": "UNVERIFIED",
  "valid_n": "UNMEASURED",
  "cold_ms": "UNMEASURED",
  "p50_ms": "UNMEASURED",
  "p95_ms": "UNMEASURED",
  "g4_status": "PARTIAL",
  "notes": "Verified earlier in PHASE9 session via /health/providers under LIMEN_RUNTIME_PROFILE=challenge: STT faster_whisper CUDA float16 ok; TTS piper reachable; LLM ollama phi3.5 reachable. Human browser mic→playback, second turn, barge-in, RED voice smoke, N>=20 remain required for G4 PASS.",
  "phi_targeted": {
    "passed": 7,
    "total": 7,
    "red_fn": []
  },
  "prior_evidence_keys": [
    "generated_at",
    "human_browser",
    "real_stt",
    "real_phi",
    "real_tts",
    "second_turn",
    "barge_in",
    "red_voice",
    "valid_n",
    "cold_ms",
    "p50_ms",
    "p95_ms",
    "g4_status",
    "providers",
    "notes",
    "phi_targeted"
  ]
}
```
