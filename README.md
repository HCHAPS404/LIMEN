# ◈ LIMEN

LIMEN is an intelligent voice-based postoperative follow-up system that turns patient conversations into structured clinical states, checks them against verifiable medical evidence, and safely determines when to continue monitoring, investigate uncertainty, or escalate the case to human care when needed.

Built for the **Tech Sphere Challenge 2026**.

> **Status:** Foundation — bootable API, a complete web application shell and design system, client accounts with per-account data scoping, provider contracts, SQLite persistence, safety governor stub, and quality gates. Backend endpoints for voice, knowledge, and TRAZA are not implemented yet; the UI states that explicitly instead of showing placeholder data.

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

### Sign in

The workspace is per-client: each account owns its own clinical corpus, so the
screens above `/` require a session ([ADR-0004](docs/adr/ADR-0004-client-auth.md)).
`make bootstrap` creates the demo account from `.env`:

| Field | Value from `.env.example` |
|-------|---------------------------|
| Email | `demo@limen.local` |
| Password | `limen-demo-2026` |

These are local demo defaults committed on purpose so a cold start reaches a call
without manual setup. Change `LIMEN_DEMO_EMAIL` / `LIMEN_DEMO_PASSWORD` before
exposing the API, or leave both empty to create no account at all. You can also
register a fresh account at http://127.0.0.1:5173/register.

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

Every surface below is implemented as UI against a typed API client. Where the
backend endpoint does not exist yet, the screen renders an explicit unavailable
state — no surface fabricates clinical data, document readiness, or metrics.

| Surface | UI | Backend |
|---------|----|---------|
| Voice Call Interface (`/call`) | Implemented — voice states, real microphone capture, level metering, barge-in, transcript | Planned — STT/TTS/turn processing |
| Knowledge Administration Console (`/knowledge`) | Implemented — upload, lifecycle states, provenance, retrieval probe, delete confirmation | Planned — `/api/knowledge/*` |
| TRAZA / Decision Trace (`/trace/:callId`) | Implemented — timeline, decision inspector, evidence, per-turn metrics | Planned — `/api/traces/*` |
| Sessions / Call History (`/sessions`) | Implemented — operational table with trace links | Planned — `/api/calls` |
| Settings / Diagnostics (`/settings`) | Implemented — preferences, runtime model, persistence, microphone test | Partial — `/health` wired |
| Landing (`/`) | Implemented — commercial entrance: hero, problem, operating loop, pillars, data isolation, honest current state | Not applicable |
| Accounts (`/login`, `/register`) | Implemented — sign in, sign up, session guard, account menu | Implemented — `/api/auth/*` |

The interface ships in Spanish and English (default Spanish) with a light and a
dark theme; both preferences are stored per browser. Clinical vocabulary returned
by the backend (`GREEN`, `UNKNOWN`, `CONFLICTING`, document status) is never
translated.

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
- Frontend colors reach components through design tokens only; a test fails the
  build on any hex literal outside `apps/web/src/styles/tokens.css`
- Risk and document states are never encoded by color alone, and knowledge
  readiness uses evidence teal so it cannot be mistaken for clinical GREEN
- Server state lives in TanStack Query; Zustand holds only microphone, playback,
  and transient call UI state
- Passwords are hashed with `hashlib.scrypt` and sessions are stored as SHA-256
  digests, so no plaintext credential or replayable token is ever persisted
- Client-owned routes depend on `require_account` and scope their queries to
  `account_id`; `/health` stays public

See [`AGENTS.md`](AGENTS.md), [`ARCHITECTURE.md`](ARCHITECTURE.md), [`BACKEND.md`](BACKEND.md), and [`FRONTEND.md`](FRONTEND.md).

## Metrics

No measured challenge metrics are claimed yet. See [`docs/EVAL_RESULTS.md`](docs/EVAL_RESULTS.md) (Planned).

## License

MIT — see [`LICENSE`](LICENSE).

## Repository

https://github.com/HCHAPS404/LIMEN
