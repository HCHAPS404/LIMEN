# LIMEN — Repository Architecture

> **Document role:** canonical repository backbone, engineering governance, quality gates, and integration contract for LIMEN.  
> **Status:** foundation specification.  
> **Priority:** this document is a source of truth. Feature work must conform to it unless an explicit architecture decision record (ADR) changes the rule.

---

<div align="center">

# ◈ LIMEN

### Repository Architecture · Engineering Rules · Quality Gates

**Build the system once. Keep every feature inside the same contract.**

</div>

---

## 0. Purpose

LIMEN is being built for the **Tech Sphere Challenge 2026** as a voice-first postoperative follow-up system with:

- real-time browser voice interaction;
- clinical knowledge retrieval (RAG);
- hot knowledge upload and removal;
- evidence provenance;
- structured clinical state;
- escalation logic;
- structured call summaries;
- measurable runtime telemetry;
- reproducible setup and evaluation.

This file defines the **technical spine** of the repository so the project does not drift into a collection of disconnected demos.

The goal is not maximum framework count. The goal is:

> **minimum operational complexity + maximum observability + clear safety boundaries + reproducible evaluation.**

---

# 1. Non-Negotiable Competition Constraints

These rules are treated as release blockers.

## 1.1 Submission gates

The final repository MUST support:

| Gate | Requirement | Repository response |
|---|---|---|
| G1 | Complete submission artifacts | repo + diagrams + final report + demo video links |
| G2 | Startup in ≤15 minutes from README | deterministic bootstrap + health verification |
| G3 | Competition-compliant runtime LLM | provider isolated behind `LLMProvider`, final model explicitly declared |
| G4 | Working real-time voice interaction | browser microphone → STT → agent → TTS |
| G5 | Live knowledge add/remove | upload → AVAILABLE → answer; delete → REMOVED → no retrieval |

## 1.2 Runtime scope

LIMEN MUST provide two required product surfaces:

1. **Voice Call Interface**
2. **Knowledge Administration Console**

Recommended differentiating surfaces:

3. **TRAZA / Decision Trace**
4. **Sessions / Call History**
5. **Settings / Diagnostics**

## 1.3 Explicitly out of scope unless time remains

Do NOT spend critical-path time on:

- real telephony;
- hospital/EHR production integration;
- enterprise authentication;
- RBAC;
- multi-tenant organizations;
- billing;
- native mobile apps;
- Kubernetes;
- microservices;
- event brokers;
- distributed databases;
- unnecessary cloud infrastructure.

The challenge rewards engineering quality around the core problem, not infrastructure volume.

---

# 2. Development Tools vs Runtime LLM

Two concepts MUST remain separate:

### Development assistance

Used for architecture, coding, review, tests, documentation, UI, debugging, and evaluation design.

### Runtime LLM

The language model invoked by LIMEN during the challenge.

The runtime LLM MUST comply with the final confirmed competition rules. It MUST be replaceable without rewriting the clinical, safety, RAG, voice, or persistence layers.

**Rule:** no source file outside `limen/intelligence/providers/` may directly import a vendor-specific LLM SDK.

---

# 3. Engineering Principles

## P1 — Modular monolith first

One deployable application, clearly separated domains.

Do not build microservices unless a demonstrated requirement cannot be solved safely within the modular monolith.

## P2 — Domain boundaries over generic folders

Prefer explicit domains:

```text
clinical/
knowledge/
safety/
voice/
tracing/
telemetry/
```

## P3 — Safety-critical logic must be testable without an LLM

The escalation layer cannot require a model call to execute deterministic safeguards.

## P4 — Unknown is a first-class state

Never coerce missing clinical information into `False`, `0`, or `"normal"`.

Use explicit states:

```text
KNOWN_NORMAL
KNOWN_ABNORMAL
UNKNOWN
CONFLICTING
```

## P5 — Evidence is data, not instruction

Patient input and retrieved documents are untrusted content.

They cannot redefine system policy or safety rules.

## P6 — Observable behavior beats hidden cleverness

If a decision cannot be reconstructed from logs, it is not production-quality challenge behavior.

## P7 — Measured claims only

README metrics MUST come from reproducible scripts/logs.

Never manually invent accuracy, recall, latency, token consumption, cost, or RAG quality.

## P8 — No dataset leakage

The public challenge labels may be used for evaluation.

They MUST NOT be used to hard-code runtime decisions.

Forbidden:

```text
if caso_id == "...": return RED
```

Forbidden:

- shipping ground-truth labels into production prompts;
- reading hidden/silver trajectory truth as if the patient had already stated it;
- manually coding patient-specific answers;
- memorizing the public evaluation cases.

---

# 4. Canonical Repository Layout

```text
limen/
│
├── README.md
├── LICENSE
├── .gitignore
├── .env.example
├── Makefile
├── pyproject.toml
├── uv.lock
├── package.json                  # optional root orchestration only
│
├── AGENTS.md                     # compact engineering charter
│
├── apps/
│   ├── api/
│   │   └── main.py
│   │
│   └── web/
│       ├── index.html
│       ├── package.json
│       ├── package-lock.json
│       ├── tsconfig.json
│       ├── vite.config.ts
│       ├── public/
│       └── src/
│
├── limen/
│   ├── __init__.py
│   ├── config/
│   ├── conversation/
│   ├── clinical/
│   ├── intelligence/
│   │   ├── contracts.py
│   │   ├── prompts/
│   │   ├── structured_output.py
│   │   └── providers/
│   ├── knowledge/
│   ├── safety/
│   ├── voice/
│   ├── tracing/
│   ├── telemetry/
│   └── persistence/
│
├── evals/
├── tests/
├── scripts/
├── docs/
│   ├── architecture/
│   ├── adr/
│   ├── assets/
│   ├── PROMPT_CHANGELOG.md
│   ├── EVAL_RESULTS.md
│   └── FINAL_REPORT.md
│
├── challenge/
│
└── runtime/                      # NEVER committed
    ├── db/
    ├── documents/
    ├── vectors/
    ├── audio/
    └── logs/
```

---

# 5. Dependency Direction

Dependencies must flow inward toward domain contracts.

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

Forbidden dependency examples:

```text
clinical/state.py        → Groq SDK
safety/governor.py       → React
knowledge/retrieval.py   → FastAPI Request
conversation/session.py  → vendor-specific LLM response object
```

---

# 6. Runtime Provider Contracts

All replaceable infrastructure MUST implement contracts.

## LLM

```python
class LLMProvider(Protocol):
    async def generate_text(self, request: LLMRequest) -> LLMResponse: ...
    async def generate_structured(
        self,
        request: LLMRequest,
        schema: type[T],
    ) -> T: ...
```

## Speech-to-Text

```python
class STTProvider(Protocol):
    async def transcribe(self, audio: bytes, language: str = "es") -> Transcript: ...
```

## Text-to-Speech

```python
class TTSProvider(Protocol):
    async def synthesize(self, text: str, voice: str) -> AudioResult: ...
```

## Embeddings

```python
class EmbeddingProvider(Protocol):
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...
    def embed_query(self, text: str) -> list[float]: ...
```

This is what allows model/provider experimentation without destabilizing the product.

---

# 7. Configuration Strategy

Use one typed settings object.

```text
.env
   ↓
Pydantic Settings
   ↓
ApplicationSettings
```

Rules:

- `.env` is local and ignored.
- `.env.example` is committed.
- secrets never appear in source.
- runtime providers are chosen by configuration.
- default development configuration must be documented.
- production-like challenge configuration must be reproducible.

Example:

```dotenv
APP_ENV=development

LLM_PROVIDER=
LLM_MODEL=
LLM_API_KEY=

STT_PROVIDER=
STT_MODEL=
STT_API_KEY=

TTS_PROVIDER=
TTS_MODEL=

DATABASE_PATH=./runtime/db/limen.db
VECTOR_PATH=./runtime/vectors
DOCUMENT_PATH=./runtime/documents
LOG_PATH=./runtime/logs

MAX_UPLOAD_MB=25
LOG_LEVEL=INFO
```

---

# 8. Engineering Charter

See root [`AGENTS.md`](AGENTS.md) for the compact shared charter.

Correctness is enforced by tests, type checking, linting, CI, `verify_submission.py`, and architecture review — not by informal convention alone.

---

# 9. Branch & Commit Discipline

Recommended branch names:

```text
feat/call-interface
feat/live-knowledge
feat/safety-governor
fix/deleted-doc-leakage
test/adversarial-suite
docs/final-report
```

Commit examples:

```text
chore: scaffold reproducible project
feat(knowledge): add document ingestion registry
feat(knowledge): enforce hard deletion from active retrieval
feat(clinical): model unknown and conflicting findings
feat(safety): add monotonic escalation governor
feat(voice): add websocket call transport
test(safety): cover ambiguous respiratory complaint
perf(voice): reduce end-of-speech to first-audio latency
docs: record model benchmark decision
```

Avoid vague messages such as `final`, `update`, `fix stuff`, or `working version`.

---

# 10. Quality Gates

A PR/feature is mergeable only when relevant checks pass.

## Backend

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy limen apps/api
uv run pytest
```

## Frontend

```bash
npm run lint
npm run typecheck
npm run test
npm run build
```

## Challenge-critical

```bash
uv run python evals/knowledge_lifecycle_eval.py
uv run python evals/adversarial_eval.py
uv run python scripts/verify_submission.py
```

Exact commands may evolve, but one canonical command must exist:

```bash
make verify
```

---

# 11. Definition of Done

A feature is **Done** only when:

- it works through the real application path;
- typed contracts exist;
- relevant tests exist;
- errors are surfaced coherently;
- telemetry exists if challenge-critical;
- docs match implementation;
- no secrets/runtime files are added;
- no architecture boundary is bypassed;
- it does not break voice or live knowledge gates.

Informal claims of “it works” are not evidence.

---

# 12. Architecture Decision Records

Create ADRs for decisions that materially change:

- database;
- vector storage;
- runtime LLM;
- STT/TTS provider;
- retrieval architecture;
- safety semantics;
- deployment model;
- repository boundaries.

Path:

```text
docs/adr/ADR-0001-<title>.md
```

Template:

```markdown
# ADR-XXXX — Title

## Status
Proposed / Accepted / Superseded

## Context

## Decision

## Alternatives considered

## Consequences

## Challenge impact

## Verification
```

---

# 13. Prohibited Engineering Shortcuts

Do NOT:

- embed API keys in source;
- put `.env` into Git;
- hard-code evaluation answers;
- use the LLM as database;
- make the LLM sole safety authority;
- mark upload AVAILABLE before indexing verification;
- "delete" knowledge only from the UI while vectors remain active;
- invent citation page numbers;
- store only a final decision without the evidence path;
- swallow provider errors and return fake successful responses;
- claim P50/P95 from one hand-timed demo;
- build visually beautiful screens with nonfunctional buttons;
- let diagrams describe components that do not exist.

---

# 14. Foundation Milestone

Before feature expansion, the repository foundation is considered complete when:

```text
[x] repo scaffold exists
[x] backend boots
[x] frontend boots
[x] typed config works
[x] SQLite initializes
[x] provider contracts compile
[x] health endpoint works
[x] base app shell renders
[x] Makefile bootstrap/run/verify targets exist
[x] CI runs lint/typecheck/tests
[x] docs folder + ADR structure exists
[x] runtime/ is ignored
[x] no secret scanning violations
```

Only after this milestone should feature development accelerate.

---

<div align="center">

## ◈ LIMEN Engineering Principle

**Architecture is not the diagram.  
Architecture is the set of constraints that still hold after the tenth feature is added.**

</div>
