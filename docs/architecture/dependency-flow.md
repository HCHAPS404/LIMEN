# Dependency flow

```text
apps/web
   │
   ▼
apps/api
   │
   ▼
conversation
   ├──────────────► clinical
   ├──────────────► knowledge
   ├──────────────► safety
   ├──────────────► voice
   └──────────────► tracing/telemetry

vendor SDKs
   │
   ▼
provider adapters
   │
   ▼
domain contracts
```

Enforced by `scripts/check_boundaries.py` in `make verify`.
