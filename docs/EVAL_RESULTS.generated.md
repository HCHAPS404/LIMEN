# EVAL RESULTS (generated)

Generated at: `2026-08-13T02:36:40.239299+00:00`
Commit: `ba80a1fe7b9a58de586505a00b8860e282a5a111`

## Methodology

```json
{
  "text_turn_latency": "StageTimer monotonic speech_end\u2192turn_end per text turn",
  "percentiles": "nearest-rank ceil(p/100 * n) on sorted latencies",
  "tokens": "provider-reported only; null when no LLM call",
  "cost": "local API cost is measured $0 (Ollama/Whisper/Piper). equivalent_api uses GPT-4o mini public list price on TRAZA tokens.",
  "voice_latency": "TRAZA voice.playback.started: client speech_end_monotonic \u2192 client audio_playback_start_monotonic. Official P50/P95 are warm (exclude first playback per call). N>=20 required to claim the challenge threshold; SERVER_TTS_READY_PROXY is not this metric."
}
```

## Summary

- Calls: 82
- Text-turn latency P50 (ms): 1891.1243290003767
- Text-turn latency P95 (ms): 9970.143206999637
- Total LLM calls: 189
- Total RAG queries: 56
- Voice latency: `measured` (warm N=84; P50=6457.0; P95=19103.0)
- Official playback events: 137 (official N=137; cold N=53)
- Tokens in/out: 204476 / 17593 (turns=137)
- Local API cost: `measured` $0.0
- Equivalent GPT-4o mini / call: 0.0007495854545454545 (https://openai.com/api/pricing/ as of 2026-08-12)

Official challenge voice P50/P95 are **warm** browser samples from TRAZA. Do not substitute SERVER_TTS_READY_PROXY.
