# LIMEN Backend

> Foundation stub derived from `ARCHITECTURE.md`. Expand with endpoint catalogs as features land.

## Stack

- FastAPI (`apps/api/main.py`)
- Domain packages under `limen/`
- Pydantic Settings (`limen/config/settings.py`)
- SQLite (`limen/persistence/database.py`)
- Provider contracts for LLM / STT / TTS / Embeddings

## Dependency direction

```text
apps/api → conversation → {clinical, knowledge, safety, voice, tracing, telemetry}
vendor SDKs → provider adapters → domain contracts
```

## Safety Governor

Module: `limen/safety/governor.py`

Non-negotiable properties:

1. Callable **without** an LLM.
2. Severity is **monotonic** (`GREEN < YELLOW < ORANGE < RED`).
3. Generative output cannot weaken a stronger floor (`enforce_floor`).
4. Rules must not hard-code challenge case IDs or labels.
5. Clinical uncertainty stays explicit (`UNKNOWN`, `CONFLICTING`).

Foundation includes a lexical rule stub for smoke tests. Full clinical policy is Planned.

## Provider selection

Configured via `.env`:

- `LLM_PROVIDER=stub|ollama`
- `STT_PROVIDER=stub`
- `TTS_PROVIDER=stub`
- `EMBEDDING_PROVIDER=stub`

## Health

`GET /health` returns status, version, env, LLM declaration, and database health.
