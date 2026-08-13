# G4 Voice Gate Evidence (generated)

Generated: 2026-08-13T04:38:19.650522+00:00

Human browser smoke: **PASS**
Real STT (faster-whisper CUDA): **PASS**
Real Phi: **PASS**
Real TTS (Piper): **PASS**
Second turn: **PASS**
Barge-in: **PARTIAL**
RED voice escalation: **PASS**
Valid browser samples N: **137**
Warm N (exclude first playback/call): **84**
Cold first turn: **8236.0**
Warm P50 (speech-end→playback): **6457.0**
Warm P95: **19103.0**
G4 status: **PASS_WITH_WARNINGS**

## Notes

Official warm browser E2E from TRAZA: N=84, P50=6457.0 ms, P95=19103.0 ms. Cross-clock tts_ready vs playback no longer excludes E2E. Barge-in subsequent remains PARTIAL.

```json
{
  "generated_at": "2026-08-13T02:36:40.239299+00:00",
  "human_browser": "PASS",
  "real_stt": "PASS",
  "real_phi": "PASS",
  "real_tts": "PASS",
  "second_turn": "PASS",
  "barge_in": "PARTIAL",
  "red_voice": "PASS",
  "valid_n": 137,
  "warm_n": 84,
  "cold_ms": 8236.0,
  "p50_ms": 6457.0,
  "p95_ms": 19103.0,
  "voice_latency_status": "measured",
  "source": "traza_voice.playback.started",
  "g4_status": "PASS_WITH_WARNINGS",
  "operator_notes": "G4 human confirmed 2026-08-09; barge-in subsequent still PARTIAL",
  "notes": "Official warm browser E2E from TRAZA: N=84, P50=6457.0 ms, P95=19103.0 ms. Cross-clock tts_ready vs playback no longer excludes E2E. Barge-in subsequent remains PARTIAL."
}
```
