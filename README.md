# ◈ LIMEN

LIMEN is an intelligent voice-based postoperative follow-up system that turns patient conversations into structured clinical states, checks them against verifiable medical evidence, and safely determines when to continue monitoring, investigate uncertainty, or escalate the case to human care when needed.

Built for the **Tech Sphere Challenge 2026**.

> **Status:** Foundation — bootable API and web shell, provider contracts, SQLite persistence, safety governor stub, and quality gates. Challenge features (full voice, live RAG, TRAZA) are labeled Planned where not yet implemented.

## Cold start (≤15 minutes)

### Prerequisites

- Python 3.11+
- Node.js 20+
- (Optional) [uv](https://github.com/astral-sh/uv) for lockfile workflows

### Bootstrap

```bash
cp .env.example .env
make bootstrap
```

### Run

```bash
# terminal 1
make dev-api

# terminal 2
make dev-web
```

| Service | URL |
|---------|-----|
| API health | http://127.0.0.1:8000/health |
| Web app | http://127.0.0.1:5173 |
| OpenAPI | http://127.0.0.1:8000/docs |

### Verify

```bash
make verify
```

## Runtime model declaration

| Role | Default (development) | Notes |
|------|----------------------|-------|
| LLM | `stub` (`LLM_PROVIDER=stub`) | Replace via `.env`; Ollama adapter available |
| STT | `stub` | Isolated behind `STTProvider` |
| TTS | `stub` | Isolated behind `TTSProvider` |
| Embeddings | `stub` | Isolated behind `EmbeddingProvider` |

Vendor SDKs may only be imported inside provider adapters. See [`ARCHITECTURE.md`](ARCHITECTURE.md).

## Product surfaces

| Surface | Status |
|---------|--------|
| Voice Call Interface | Planned (shell route present) |
| Knowledge Administration Console | Planned (shell route present) |
| TRAZA / Decision Trace | Planned (shell route present) |
| Sessions / Call History | Planned (shell route present) |
| Settings / Diagnostics | In Progress (API health wired) |

## Repository map

```text
apps/api          FastAPI entrypoint
apps/web          React + Vite UI
limen/            Domain packages (clinical, knowledge, safety, voice, …)
evals/            Reproducible challenge evaluations
tests/            unit / integration / contract / safety / e2e
scripts/          bootstrap + verify gates
docs/             architecture, ADRs, reports
```

## Engineering notes

- Modular monolith with explicit domain boundaries
- Safety escalation is deterministic and must not depend on an LLM
- Clinical uncertainty is first-class (`UNKNOWN`, `CONFLICTING`)
- Metrics in this README must come from evaluation scripts only

See [`AGENTS.md`](AGENTS.md), [`ARCHITECTURE.md`](ARCHITECTURE.md), [`BACKEND.md`](BACKEND.md), and [`FRONTEND.md`](FRONTEND.md).

## Metrics

No measured challenge metrics are claimed yet. See [`docs/EVAL_RESULTS.md`](docs/EVAL_RESULTS.md) (Planned).

## License

MIT — see [`LICENSE`](LICENSE).

## Repository

https://github.com/HCHAPS404/LIMEN
