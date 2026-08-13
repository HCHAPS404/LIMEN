# Cost / call (generated)

Generated at: `2026-08-13T02:36:40.239299+00:00`
Commit: `ba80a1fe7b9a58de586505a00b8860e282a5a111`

## Local challenge runtime

- API cost: **$0.0** (`measured`)
- Notes: `local_runtime_api_cost_zero`
- Providers: Ollama + faster-whisper + Piper on the host. No cloud LLM invoice.

## Token usage from TRAZA

- Input tokens: **204476**
- Output tokens: **17593**
- Turns with provider tokens: **137**
- Calls with provider tokens: **55**
- Mean in/out per token-turn: 1492.5 / 128.4

## Equivalent API (not a LIMEN invoice)

- Model: `gpt-4o-mini`
- List price: $0.15 / $0.6 per 1M tokens (input / output)
- Source: https://openai.com/api/pricing/ (as of 2026-08-12)
- Total equivalent over harvested tokens: **$0.041227**
- Equivalent per call (calls with tokens): **$0.000750**

This is an extrapolation from measured Ollama token counts onto a public cloud list price. It is not a billed LIMEN statement.
