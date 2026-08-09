# G4 Voice Gate Evidence (generated)

Generated: 2026-08-09T06:31:00+00:00

Human browser smoke: **PASS** (operator 2026-08-09)
Real STT (faster-whisper CUDA): **PASS**
Real Phi: **PASS**
Real TTS (Piper): **PASS**
Second turn: **PASS**
Barge-in: **PARTIAL** (first interrupt OK; subsequent interrupts still unreliable)
RED voice escalation: **PASS** (exercised in prior operator turns / scripted RED line)
Valid browser samples N: **UNMEASURED** (≥20 warm P50/P95 not collected this round)
Cold first turn: **UNMEASURED**
Warm P50 (speech-end→playback): **UNMEASURED**
Warm P95: **UNMEASURED**
G4 status: **PASS WITH WARNINGS**

## Notes

Operator confirmed real browser voice on challenge runtime after echo/RAG/stability fixes.
Multi-turn clinical conversation worked (pain 7→4, wound, GREEN/YELLOW path). Residual polish:
subsequent barge-in reliability; ≥20 warm latency samples still unmeasured.
Personality/voice pass landed after G4 confirm: preferred-name capture, usted + anti-3ª persona
validator, patient_response_v7, Piper prosody/silence/fades (no naturalness metrics claimed).

```json
{
  "generated_at": "2026-08-09T06:31:00+00:00",
  "human_browser": "PASS",
  "real_stt": "PASS",
  "real_phi": "PASS",
  "real_tts": "PASS",
  "second_turn": "PASS",
  "barge_in": "PARTIAL",
  "red_voice": "PASS",
  "valid_n": "UNMEASURED",
  "cold_ms": "UNMEASURED",
  "p50_ms": "UNMEASURED",
  "p95_ms": "UNMEASURED",
  "g4_status": "PASS_WITH_WARNINGS",
  "operator_notes": "G4 human confirmed with residual barge-in/UX polish items"
}
```
