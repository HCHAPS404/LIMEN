# ◈ LIMEN

LIMEN is a **browser-based postoperative follow-up agent** for the
**Tech Sphere Challenge 2026**. It turns patient speech into an explicit clinical
state, checks living medical knowledge with provenance, and escalates through a
**deterministic Safety Governor** — not through unconstrained LLM judgment.

> **Not a medical device.** Not a replacement for a clinician.

## What problem it solves

After surgery, patients need timely follow-up. Clinicians cannot call everyone.
LIMEN provides always-available Spanish voice follow-up that is **evidence-aware**,
**traceable (TRAZA)**, and **conservative on risk** (false negatives on RED are
treated as more severe than false positives).

## Demo / screenshots

Demo script and shot list: [`docs/submission/DEMO_SCRIPT.md`](docs/submission/DEMO_SCRIPT.md),
[`docs/submission/VIDEO_SHOT_LIST.md`](docs/submission/VIDEO_SHOT_LIST.md).

Screenshots / video: `FINAL_EVIDENCE_REQUIRED:DEMO_VIDEO` /
see [`docs/submission/SCREENSHOT_REGISTER.md`](docs/submission/SCREENSHOT_REGISTER.md).

## Architecture

Modular monolith: React browser UI + FastAPI + domain packages under `limen/`.

```text
Browser (mic, VAD, playback)
  → WebSocket voice
  → Faster-Whisper STT
  → ClinicalState + Uncertainty
  → Hybrid RAG (E5 + Qdrant + FTS5 + RRF)
  → Safety Governor (authoritative)
  → Phi-3.5 or deterministic templates
  → Piper TTS → browser
  → TRAZA + SQLite metrics
```

Diagrams: [`docs/submission/ARCHITECTURE.md`](docs/submission/ARCHITECTURE.md) ·
[`DECISION_FLOW.md`](docs/submission/DECISION_FLOW.md) ·
[`KNOWLEDGE_FLOW.md`](docs/submission/KNOWLEDGE_FLOW.md) ·
[`TRAZA.md`](docs/submission/TRAZA.md)

Full SoT: [`ARCHITECTURE.md`](ARCHITECTURE.md), [`BACKEND.md`](BACKEND.md),
[`FRONTEND.md`](FRONTEND.md).

## Key safety principle

**`unknown != normal`.** Missing information stays `UNKNOWN`.

**The LLM cannot downgrade deterministic safety.** Phi-3.5 phrases replies under
trusted application state; `SafetyGovernor.enforce_floor` owns
GREEN / YELLOW / RED and escalation.

Official **model-only** advisory benchmark (not LIMEN full-system recall):

| Model | Macro F1 | RED recall | RED FN |
| --- | ---: | ---: | ---: |
| llama3.2:1b | 0.303 | 0.000 | 24/24 |
| llama3.2:3b | 0.197 | 0.000 | 24/24 |
| **phi3.5** | **0.445** | **0.375** | **15/24** |

Source: [`docs/MODEL_SELECTION.md`](docs/MODEL_SELECTION.md).

## Features

- Adaptive Spanish voice conversation (browser mic → STT → TTS)
- Hybrid RAG with provenance
- Live knowledge upload / delete / forget (admin console)
- Deterministic escalation + structured call summary
- TRAZA decision timeline
- Challenge runtime profile (`LIMEN_RUNTIME_PROFILE=challenge`)

## Challenge requirements coverage

| Requirement | LIMEN |
| --- | --- |
| Adaptive voice conversation | `/call` + WS stream + ConversationContext |
| RAG | HybridEvidenceRetriever (E5 + FTS5 + RRF) |
| Live upload | `/knowledge` + knowledge API lifecycle |
| Delete / forget | Deletion service purges lexical + vector indexes |
| Traceability | TRAZA UI + `/api/traces/{id}` |
| Escalation | SafetyGovernor RED + persisted artifact |
| Structured summary | Call finish → summary endpoint/UI |
| Spanish | Product UI + patient prompts (CO-oriented) |
| Regional robustness | Eval scenarios; no hard-coded challenge slang branches |
| Voice browser / API | Faster-Whisper + Piper; stubs for CI |
| Public repository | This repo + MIT license |
| Dependencies | `pyproject.toml`, `apps/web/package.json`, `.env.example` |

## Quick start (development stubs OK)

```bash
cp .env.example .env
make bootstrap
make run          # API :8000
make dev-web      # Web :5173
```

Demo login (from `.env.example`): `demo@limen.local` / `limen-demo-2026`

## Challenge runtime (real stack)

### System prerequisites (before G2 timer)

Python 3.11+, Node 20+, Ollama running, NVIDIA GPU/driver for CUDA STT, network
for first-time model pulls. Docker not required.

```bash
cp .env.example .env
# optional: export LIMEN_DATASET_PATH=/absolute/path/to/official/dataset

make bootstrap
make prepare-voice
make prepare-llm-bench PULL=1
make prepare-knowledge
make verify-challenge-environment   # READY_FOR_CHALLENGE_RUNTIME=TRUE
make run-challenge                  # API + web
```

Measured clean-worktree bootstrap (host caches may be warm): **293.85 s** —
[`docs/G2_BOOTSTRAP.generated.md`](docs/G2_BOOTSTRAP.generated.md).  
Strict fresh-machine clone: `FINAL_EVIDENCE_REQUIRED:G2_STRICT_CLONE`.

More: [`docs/CHALLENGE_RUNTIME.md`](docs/CHALLENGE_RUNTIME.md).

## Knowledge management

- Seed: `make prepare-knowledge`
- Official PDFs: `LIMEN_DATASET_PATH=... make prepare-official-knowledge`  
  Discovered **107**; smoke indexed **8** (not 107/107 yet) —
  `FINAL_EVIDENCE_REQUIRED:OFFICIAL_CORPUS_FULL`
- Live G5: admin UI `/knowledge` —
  `FINAL_EVIDENCE_REQUIRED:G5_UI`

## Voice

faster-whisper-small (CUDA float16) · Piper `es_MX-claude-high` · browser VAD ·
WebSocket barge-in / stale-response protection.

Official challenge latency (speech-end → browser playback start):

| | |
| --- | --- |
| P50 | `FINAL_EVIDENCE_REQUIRED:G4_P50` |
| P95 | `FINAL_EVIDENCE_REQUIRED:G4_P95` |

Server TTS-ready proxies are **not** official challenge latency.

## Safety / escalation

Deterministic rules + structured findings → SafetyDecision → templates/Phi under
floor → validator. RED cannot be downgraded by generative output.

## TRAZA / observability

`/trace/:callId` reconstructs extraction, retrieval, safety, response, and voice
events without chain-of-thought. Challenge-critical timings are preserved.

## Metrics

| Metric | Status |
| --- | --- |
| Voice P50 / P95 (browser) | UNMEASURED — `FINAL_EVIDENCE_REQUIRED:G4_P50` / `G4_P95` |
| Input / output tokens | Per-turn when provider reports usage; often null today |
| LLM calls / RAG queries | Instrumented per turn/call |
| Cost / call | `FINAL_EVIDENCE_REQUIRED:COST_CALL` (SOURCE_REQUIRED) |

## Model selection

Primary runtime LLM: **Phi-3.5 Mini via Ollama** (`phi3.5`).  
Safety authority: **Safety Governor**, not Phi.  
Details: [`docs/MODEL_SELECTION.md`](docs/MODEL_SELECTION.md).

## Testing

```bash
make verify                  # lint, types, tests (stub embeddings)
make verify-challenge-eval   # PHASE 8 challenge scenarios
make verify-phase7           # golden E2E (stub CI path)
make verify-submission-evidence  # unresolved FINAL_EVIDENCE_REQUIRED markers
```

## Project structure

```text
apps/api     FastAPI
apps/web     React + Vite UI
limen/       Domain packages
evals/       Challenge / RAG / LLM / voice evaluations
tests/       unit · integration · safety
docs/        architecture, ADRs, generated metrics, submission/
scripts/     bootstrap, prepare-*, verify-*
```

## Limitations

Not a medical device; local-model language limits; browser voice P50/P95 still
unmeasured; safety rules need broader clinical validation; knowledge quality
depends on corpus; full official PDF ingest not verified at 107/107; human
clinical validation is outside hackathon scope.

## Reproducibility

Challenge profile forces real providers (no stub READY). Evaluation artifacts are
generated under `docs/*.generated.md` and `runtime/evals/`. Submission package:
[`docs/submission/`](docs/submission/). Final polish queue:
[`docs/FINAL_POLISH_REGISTER.md`](docs/FINAL_POLISH_REGISTER.md).

## License

MIT — see [`LICENSE`](LICENSE). Third-party models/tools:
[`docs/submission/ATTRIBUTION.md`](docs/submission/ATTRIBUTION.md).

## Repository

https://github.com/HCHAPS404/LIMEN
