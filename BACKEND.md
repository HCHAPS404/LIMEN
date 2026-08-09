# LIMEN — Backend Architecture & Clinical Intelligence Platform

> **Document role:** canonical backend architecture, domain model, APIs, RAG lifecycle, voice pipeline, Safety Governor, persistence, telemetry, testing, and integration rules.  
> **Status:** foundation specification.  
> **Applies to:** `apps/api/**`, `limen/**`, `evals/**`, backend-facing `scripts/**`

---

<div align="center">

# ◈ LIMEN / BACKEND

### Evidence · State · Safety · Voice · Traceability

**The backend is responsible for making the demo difficult to break.**

</div>

---

# 1. Backend Objective

The backend must satisfy the challenge core with the smallest reliable operational footprint.

Primary responsibilities:

- real-time voice session orchestration;
- speech-to-text integration;
- structured clinical state;
- adaptive follow-up;
- clinical evidence retrieval;
- hot knowledge ingestion/deletion;
- source provenance;
- safety decision logic;
- escalation artifacts;
- text-to-speech;
- structured call summary;
- telemetry and cost accounting;
- reproducible evaluation.

---

# 2. Architecture Style

## Decision

**Python modular monolith with FastAPI as the transport edge.**

Why:

- fast implementation;
- strong AI/document ecosystem;
- easy typed schemas;
- WebSocket support;
- one process can serve API + built frontend;
- reproducible;
- no infrastructure tax.

---

# 3. Canonical Backend Stack

| Domain | Technology |
|---|---|
| Python | 3.11+ |
| API | FastAPI |
| Validation | Pydantic v2 |
| Settings | pydantic-settings |
| ORM | SQLAlchemy 2 |
| Relational DB | SQLite, WAL mode |
| Dense vector storage | Qdrant local/client mode |
| Lexical retrieval | SQLite FTS5 or explicit BM25 layer |
| PDF extraction | PyMuPDF |
| OCR fallback | OCR adapter, invoked only when needed |
| LLM | provider abstraction |
| STT | provider abstraction |
| TTS | provider abstraction |
| HTTP client | httpx |
| Logging | structured JSON logging |
| Tests | pytest / pytest-asyncio |
| Lint | Ruff |
| Type check | mypy or pyright |
| Package manager | uv |

Provider choices may be benchmarked and changed without changing domain contracts.

---

# 4. Backend Modules

```text
limen/
├── config/
├── conversation/
├── clinical/
├── intelligence/
├── knowledge/
├── safety/
├── voice/
├── tracing/
├── telemetry/
└── persistence/
```

Each module owns one domain.

---

# 5. API Edge

FastAPI handles:

- transport validation;
- dependency injection;
- HTTP status mapping;
- WebSocket lifecycle;
- health endpoints.

FastAPI does NOT own:

- clinical reasoning;
- RAG logic;
- safety decisions;
- vendor-specific behavior.

---

# 6. API Surface

## 6.1 Monorepo reconciliation (authoritative for this repo)

The draft surface below used `/api/v1`. The **implemented transport** matches
`FRONTEND.md` and the browser client under `apps/web/src/api/`:

```text
/api/...          HTTP product routes
/health           liveness (public)
WS /api/calls/{call_id}/stream
/api/auth/*       client accounts (ADR-0004; not in the original draft tree)
```

Do **not** introduce `/api/v1` until an ADR migrates frontend and backend together.

Additional stable contracts used by the UI today:

```http
GET /api/knowledge/retrieval-probe?query=...
DELETE /api/auth/me
```

Risk lattice in this monorepo (frontend + Safety Governor):

```text
GREEN < YELLOW < ORANGE < RED
```

Stack **actual** vs **target**:

| Concern | Actual (Implemented) | Target (Planned) |
|---|---|---|
| Relational store | `sqlite3` + WAL + schema v3 (ADR-0005) | SQLAlchemy 2 |
| Dense vectors | `QdrantVectorStore` (local path) + stub / CPU-first `sentence-transformers` (`intfloat/multilingual-e5-small`) | Optional heavier models (e.g. BGE-M3); CUDA optional |
| Lexical retrieval | SQLite FTS5 (Implemented) | — |
| Hybrid fusion | `HybridEvidenceRetriever` + RRF (Implemented) | Optional reranker (not yet) |
| Auth | cookie session (`limen/auth`) | same (challenge-scoped) |

Status labels in later sections mean: **Implemented** only when code + tests exist;
everything else stays **Planned** / **In Progress**.

## 6.2 Product routes

Base prefix for product routes:

```text
/api
```

## Health

```http
GET /health
GET /health/ready
GET /health/providers
```

## Auth (ADR-0004)

```http
POST   /api/auth/register
POST   /api/auth/login
POST   /api/auth/logout
GET    /api/auth/me
DELETE /api/auth/me
```

## Calls

```http
POST /api/calls
GET  /api/calls
GET  /api/calls/{call_id}
POST /api/calls/{call_id}/finish
GET  /api/calls/{call_id}/summary
```

## Voice

```text
WS /api/calls/{call_id}/stream
```

## Knowledge

```http
GET    /api/knowledge/documents
POST   /api/knowledge/documents
GET    /api/knowledge/documents/{document_id}
DELETE /api/knowledge/documents/{document_id}
GET    /api/knowledge/retrieval-probe
```

## Trace

```http
GET /api/traces/{call_id}
```

## Metrics

```http
GET /api/metrics/calls/{call_id}
GET /api/metrics/summary
```

Do not add endpoints until an actual product flow needs them.

---

# 7. Conversation Orchestrator

`limen/conversation/orchestrator.py`

**Status (text turn):** Implemented — async pipeline
`extract → uncertainty_analysis → gated retrieval (EvidenceRetriever) →
SafetyGovernor.enforce_floor → response (escalation template or stub LLM)` with
TRAZA stages and `POST /api/calls/{call_id}/turns`. Lexical FTS is the current
`EvidenceRetriever` adapter; dense/hybrid Planned. Voice STT/TTS remains
stub/planned polish.

The orchestrator coordinates domains.

It should not contain all business logic.

Conceptual flow:

```text
transcript
   ↓
clinical extraction
   ↓
state update
   ↓
uncertainty analysis
   ↓
retrieve evidence if needed
   ↓
safety evaluation
   ↓
choose next action
   ↓
generate patient-facing response
   ↓
TTS
   ↓
trace + telemetry
```

---

# 8. Clinical State

The conversation history is not the clinical state.

Create an explicit typed representation.

Example:

```python
class ObservationStatus(str, Enum):
    KNOWN_NORMAL = "known_normal"
    KNOWN_ABNORMAL = "known_abnormal"
    UNKNOWN = "unknown"
    CONFLICTING = "conflicting"
```

Representative state:

```python
class ClinicalState(BaseModel):
    patient_id: str
    procedure: str | None
    postoperative_day: int | None

    pain: PainState
    temperature: TemperatureState
    wound: WoundState
    respiratory: RespiratoryState
    mobility: MobilityState
    intake: IntakeState

    unresolved_questions: list[str]
    red_flags: list[str]
```

---

# 9. Clinical Extraction

The extractor converts natural language into candidate structured updates.

It MUST NOT directly decide final risk.

Input:

```text
existing clinical state
latest patient utterance
relevant conversation context
```

Output:

```json
{
  "observations": [],
  "conflicts": [],
  "uncertainties": [],
  "candidate_followups": []
}
```

Structured output validation is mandatory.

If the model returns invalid structure:

- retry with bounded policy;
- record failure;
- never silently coerce dangerous fields.

---

# 10. Uncertainty Model

Rules:

- missing ≠ negative;
- "I don't know" → UNKNOWN;
- two incompatible statements → CONFLICTING;
- subjective fever ≠ measured fever;
- family member statement may be stored with source metadata;
- low-confidence transcription may trigger clarification.

Uncertainty is used by Question Policy.

---

# 11. Adaptive Question Policy

Purpose:

Ask the **next most useful question**, not a full static questionnaire.

Inputs:

- clinical state;
- unresolved fields;
- potential severity;
- procedure/day context;
- evidence availability;
- conversation length.

Policy output:

```python
class NextAction(BaseModel):
    kind: Literal[
        "ASK",
        "RESPOND",
        "ESCALATE",
        "CLOSE"
    ]
    target: str | None
    reason: str
```

Conversation brevity is a product constraint.

Default:

- one primary clinical question per turn;
- short spoken responses;
- long instructions segmented.

---

# 12. Safety Governor

`limen/safety/governor.py`

This is a critical architectural boundary.

The LLM is not allowed to directly overwrite the final risk.

## Risk lattice

```text
GREEN < YELLOW < ORANGE < RED
```

## Inputs

- structured clinical state;
- deterministic safety signals;
- evidence-supported model assessment;
- unresolved high-impact uncertainty;
- policy context.

## Output

```python
class SafetyDecision(BaseModel):
    level: Literal["GREEN", "YELLOW", "RED"]
    escalate: bool
    reasons: list[str]
    unresolved_uncertainties: list[str]
    evidence_refs: list[str]
    next_action: str
```

## Monotonic rule

Conceptually:

```python
final_level = max(
    deterministic_level,
    evidence_supported_level,
    key=severity_rank,
)
```

A weaker generative classification cannot downgrade a stronger deterministic signal.

---

# 13. Safety Rule Policy

Rules MUST be:

- explicit;
- versioned;
- testable;
- source/documentable;
- independent of public challenge case IDs.

Do not reverse-engineer runtime rules from individual labeled examples.

Use the challenge corpus and reasonable postoperative safety policy as evidence inputs.

Any safety rule modification requires regression tests.

---

# 14. Escalation Artifact

Escalation does not require real hospital integration.

Persist a structured event:

```json
{
  "alert_id": "...",
  "call_id": "...",
  "patient_id": "...",
  "severity": "RED",
  "reasons": [],
  "evidence": [],
  "created_at": "...",
  "status": "PENDING_HUMAN_REVIEW"
}
```

The patient-facing response and operator artifact are separate concerns.

---

# 15. Knowledge Architecture

The knowledge subsystem must prove:

```text
learn new document
forget deleted document
trace answer to source
```

Modules:

```text
registry.py
ingestion.py
parsing.py
ocr.py
chunking.py
embeddings.py
lexical.py
retrieval.py
fusion.py
provenance.py
deletion.py
```

---

# 16. Document Registry

**Status (PHASE 2 / 2.1):** Implemented — async accept (`PROCESSING` observable) via
in-process `KnowledgeJobRunner` thread pool; AVAILABLE after verified indexing.
Startup marks orphaned PROCESSING as `FAILED(interrupted_processing)`.
OCR: local Tesseract via PyMuPDF page rasterization when extractable text is
insufficient; dense vectors remain Planned.

Every document gets:

```text
document_id
filename
sha256
status
active_version
created_at
updated_at
```

Version:

```text
version_id
document_id
version_number
content_hash
page_count
chunk_count
status
indexed_at
removed_at
```

Status:

```text
UPLOADED
PROCESSING
AVAILABLE
FAILED
REMOVING
REMOVED
```

---

# 17. Ingestion Pipeline

```text
upload
  ↓
validate MIME / size
  ↓
sha256
  ↓
deduplicate
  ↓
registry = PROCESSING
  ↓
extract text
  ↓
OCR fallback if page text insufficient
  ↓
normalize
  ↓
page-aware chunking
  ↓
dense embedding
  ↓
lexical indexing
  ↓
persist provenance
  ↓
verify indexed chunks
  ↓
registry = AVAILABLE
```

`AVAILABLE` is set only after successful index verification.

---

# 18. PDF Parsing

Primary:

```text
PyMuPDF
```

Preserve:

- page number;
- document ID;
- section heading when detectable;
- character offsets where useful.

OCR is a fallback, not a default.

Trigger OCR only when extraction indicates a scanned/empty page.

---

# 19. Chunking

Do not chunk by arbitrary character count only.

Use:

- page boundary awareness;
- paragraph/heading boundaries;
- overlap where needed;
- stable `chunk_id`.

Example metadata:

```json
{
  "chunk_id": "...",
  "document_id": "...",
  "version_id": "...",
  "page": 17,
  "section": "Warning signs",
  "active": true,
  "sha256": "..."
}
```

---

# 20. Hybrid Retrieval

Recommended design:

```text
query
  ├── dense retrieval
  └── lexical retrieval
          ↓
       RRF fusion
          ↓
      candidate set
          ↓
   evidence selection
```

Why:

- dense retrieval handles everyday Spanish and semantic equivalents;
- lexical retrieval handles exact clinical terms, numbers, procedure names;
- fusion reduces dependence on one retrieval mode.

---

# 21. Evidence Object

Retrieval returns typed evidence, not raw strings.

```python
class Evidence(BaseModel):
    chunk_id: str
    document_id: str
    version_id: str
    filename: str
    page: int | None
    section: str | None
    text: str
    score: float
    retrieval_modes: list[str]
```

---

# 22. Provenance

Every clinically relevant generated statement should be able to reference evidence.

At minimum persist:

```text
response_turn_id
evidence_chunk_id
document_id
page
version_id
```

Never invent page numbers or citations.

---

# 23. Knowledge Deletion

**Status (PHASE 2):** Implemented — `REMOVING` → purge FTS/active chunks →
verify zero active hits → `REMOVED`. Dense vector purge Planned (null store).
Forgetting verified by integration probe `ZXQ-417`.

Deletion is a challenge gate, not a cosmetic CRUD operation.

Pipeline:

```text
DELETE
  ↓
mark REMOVING
  ↓
deactivate version
  ↓
delete dense vectors
  ↓
delete lexical index rows
  ↓
invalidate caches
  ↓
verify zero active retrieval hits
  ↓
mark REMOVED
```

An automated test must prove:

```text
before delete → new fact retrievable
after delete  → new fact not retrievable
```

---

# 24. Prompt Injection Policy

Trust hierarchy:

```text
system safety policy
        >
application contracts
        >
Safety Governor
        >
validated evidence
        >
patient input / document content
```

Patient utterances and document text are **data**.

They cannot:

- reveal system prompts;
- disable safety rules;
- change provider configuration;
- instruct the application to ignore higher-level policy.

Add adversarial tests for direct and indirect injection.

---

# 25. Runtime LLM Layer

Provider-neutral.

```text
limen/intelligence/contracts.py
limen/intelligence/providers/*
```

Responsibilities:

- text generation;
- structured generation;
- usage accounting;
- latency tracking;
- error normalization.

Domain code sees only LIMEN types.

Final challenge model is configuration-driven after PHASE 5 / 5C.2 selection.
**Selected runtime LLM:** `phi3.5` via `OllamaLLMProvider` (`LLM_PROVIDER=ollama`,
`LLM_MODEL=phi3.5`). Default settings/CI remain `LLM_PROVIDER=stub`.

See `docs/MODEL_SELECTION.md`. Official advisory metrics proved small LLMs are
**not** reliable standalone RED/YELLOW/GREEN classifiers; Safety Governor remains
authoritative. Production safety fallback is deterministic templates (not another
model). If Ollama is unreachable, LIMEN enters `DEGRADED_LLM_MODE` while Safety,
RAG, and templates stay operational.

Operator workflow (benchmark / selection — do not re-run unless requested):

```bash
make verify-llm-environment
make prepare-llm-bench          # list missing G3 tags
make prepare-llm-bench PULL=1   # opt-in ollama pull of llama3.2:1b / 3b / phi3.5 only
make verify-llm-bench           # serial fair benchmark + artifacts
```

Benchmark artifacts: `runtime/benchmarks/llm/`, `docs/LLM_BENCHMARK.generated.md`,
`docs/LLM_BENCHMARK_OFFICIAL.generated.md`.
Advisory risk scoring in the harness is **benchmark-only** and must not enter
`SafetyDecision`.

---

# 26. Prompt Architecture

Avoid one giant prompt.

Use explicit prompt purposes:

```text
clinical_extraction
evidence_answering
response_generation
summary_generation
```

Safety remains outside the response-generation prompt.

Version prompts:

```text
prompt_name
version
hash
```

Record prompt version in trace/evaluation metadata.

---

# 27. Voice Pipeline

Conceptual:

```text
Browser microphone
      ↓
VAD / utterance boundary (client)
      ↓
WebSocket /api/calls/{call_id}/stream
      ↓
STT provider (faster-whisper | stub)
      ↓
Transcript → CallService.process_text_turn
      ↓
Validated response text
      ↓
TTS provider (piper | stub)
      ↓
Audio → Browser playback
```

Challenge providers (opt-in): see `docs/VOICE_RUNTIME.md`.
CI default remains stub STT/TTS. Voice latency speech_end→first_audio is measured
from real client timestamps when samples exist; otherwise UNMEASURED.

---

# 28. STT

STT adapter output:

```python
class Transcript(BaseModel):
    text: str
    language: str
    confidence: float | None
    duration_ms: int
    provider_metadata: dict[str, Any]
```

Do not expose raw vendor response throughout the app.

If confidence is poor/unsupported:

- preserve transcript;
- allow conversation logic to request clarification.

---

# 29. TTS

TTS output:

```python
class AudioResult(BaseModel):
    audio: bytes
    mime_type: str
    duration_ms: int | None
```

Patient-facing speech should be:

- short;
- calm;
- clear;
- non-dismissive;
- non-alarmist.

---

# 30. Barge-In

Required for a premium voice experience.

If patient speech begins while TTS is playing:

1. stop browser playback;
2. cancel remaining TTS delivery when feasible;
3. record `agent.interrupted`;
4. process patient audio;
5. preserve trace continuity.

---

# 31. Persistence

SQLite is the default because it minimizes setup complexity.

Enable WAL mode.

Representative tables:

```text
calls
turns
clinical_state_snapshots

documents
document_versions

alerts
citations

trace_events
telemetry_events
provider_usage
```

Do not store vector payload twice unless necessary.

---

# 32. Representative Relational Model

## calls

```text
id
patient_id
procedure
postoperative_day
status
started_at
ended_at
final_risk
escalated
```

## turns

```text
id
call_id
sequence
speaker
transcript
response_text
created_at
```

## clinical_state_snapshots

```text
id
call_id
turn_id
state_json
created_at
```

## trace_events

```text
id
call_id
turn_id
event_type
payload_json
created_at
```

---

# 33. TRAZA

TRAZA is the audit layer (`schema_version = 1` on events).

Persisted call events use legacy `stage` names for UI compatibility and
canonical `event_type` namespaces (e.g. `turn.received`,
`clinical.extraction.completed`, `retrieval.evidence.selected`,
`safety.evaluation.completed`, `response.generation.completed`,
`call.completed`). Knowledge lifecycle events live in `knowledge_events`
(`knowledge.uploaded` … `knowledge.removed`).

Events are immutable append-style records with optional `turn_id`,
`duration_ms`, `status`, and typed `payload` (no chain-of-thought).

Voice stages (`agent.audio.*`, STT/TTS) are schema-ready but **not emitted**
until voice is implemented.

---

# 34. Required Telemetry

The challenge requires metrics that can be verified.

Text-turn timings (Implemented, monotonic `StageTimer`):

```text
clinical_ms, uncertainty_ms, retrieval_ms (dense/lexical/fusion),
safety_ms, response_generation_ms, persistence_ms, total_latency_ms
```

Voice challenge latency remains **not implemented**:

```text
patient speech end → agent audio start
```

Do not publish voice P50/P95 until those events exist. Text-turn P50/P95 may
be reported separately as engineering metrics
(`scripts/generate_metrics_report.py`).

---

# 35. Usage Metrics

Per turn and per call (null when unavailable — never fabricate tokens/cost):

- input tokens / output tokens (provider-reported only);
- LLM invocations;
- RAG queries;
- selected evidence counts;
- cost_basis: `measured` | `estimated` | `not_available` | `synthetic`.

STT/TTS usage fields are reserved; voice events are not emitted yet.

---

# 36. Cost Model

Every provider adapter should expose usage needed to estimate cost.
Until pricing is configured, `estimated_cost_usd` stays `null` with
`cost_basis=not_available`. Local runtime API cost may be measured as `0`
only when explicitly marked as local.

If local:

- runtime API cost may be zero;
- README should document production-equivalent cost methodology when required.

Never mix estimated and measured values without labels.

---

# 37. Structured Call Summary

At call completion:

```json
{
  "patient": {
    "patient_id": "...",
    "procedure": "...",
    "postoperative_day": 3
  },
  "reported_findings": [],
  "negative_findings": [],
  "unknown_findings": [],
  "conflicting_findings": [],
  "risk": "YELLOW",
  "escalated": true,
  "reasons": [],
  "evidence": [],
  "next_steps": [],
  "metrics": {}
}
```

Summary generation may use an LLM, but final risk comes from Safety Governor state.

---

# 38. Error Taxonomy

Normalize errors.

Examples:

```text
ProviderUnavailable
ProviderTimeout
InvalidStructuredOutput

DocumentTooLarge
UnsupportedDocument
DocumentParseFailed
DocumentIndexFailed

KnowledgeNotReady
EvidenceUnavailable

InvalidCallState
VoiceSessionDisconnected
```

Map to HTTP/WebSocket at the transport edge.

---

# 39. Retry Policy

Retries are bounded.

Do not recursively retry indefinitely.

Suggested principles:

- STT transient provider error: limited retry;
- LLM invalid structure: one/two structured retries;
- document indexing: controlled retry with status visible;
- safety evaluation: never silently skip due to provider failure.

If the system cannot safely determine, degrade toward clarification/human review, not false reassurance.

---

# 40. Security

- validate upload MIME/type/size;
- sanitize filenames;
- generate internal document IDs;
- never execute uploaded content;
- no shell construction from filenames;
- secrets only through environment;
- CORS locked to expected local/demo origins;
- no raw stack traces in frontend;
- no PHI assumptions; challenge data is synthetic.

---

# 41. Evaluation Harness

Treat the official challenge dataset primarily as a reproducible evaluation asset.

## Triage

Measure:

- accuracy;
- macro F1;
- GREEN recall;
- YELLOW recall;
- RED recall;
- RED false negatives.

## Robustness

Compare clean/noisy layers.

```text
robustness_drop = clean_score - noisy_score
```

## RAG

Measure:

- Hit@K;
- MRR;
- citation validity;
- unsupported claim behavior;
- deleted-document leakage.

## Voice

Measure:

- P50/P95;
- error rates;
- interruption behavior.

---

# 42. Test Layers

## Unit

- clinical state merge;
- uncertainty;
- severity ordering;
- chunk metadata;
- RRF fusion;
- cost calculations.

## Integration

- SQLite;
- vector store;
- upload/index;
- delete/forget;
- provider adapters with fakes.

## Safety

- ambiguous symptoms;
- contradictory statements;
- injection;
- dangerous downgrade attempt;
- unsupported evidence.

## Contract

- API schema;
- WebSocket events;
- frontend-facing types.

## E2E

- call smoke;
- knowledge lifecycle;
- trace availability.

---

# 43. Provider Fakes

Every external provider needs a deterministic fake for tests.

```text
FakeLLMProvider
FakeSTTProvider
FakeTTSProvider
FakeEmbeddingProvider
```

CI must not require paid API credentials for core tests.

---

# 44. Health & Readiness

`/health`

Application process alive.

`/health/ready`

Core dependencies initialized:

- DB;
- vector store;
- configuration.

`/health/providers`

Diagnostic view for:

- LLM;
- STT;
- TTS.

Provider health must not leak secrets.

---

# 45. Startup Strategy

Goal: evaluator can start LIMEN quickly.

Preferred UX:

```bash
cp .env.example .env
make bootstrap
make run
```

`make bootstrap`:

```text
install locked backend deps
install/build frontend
initialize DB
prepare local provider assets
initialize knowledge store
optionally ingest official corpus
run health check
```

`make run`:

```text
start FastAPI
serve built frontend
print URL
```

One URL is preferable.

---

# 46. Build Strategy

For submission:

- build React ahead or during bootstrap;
- FastAPI may serve static frontend build;
- avoid requiring two manually managed terminals if possible.

Development can still use:

```text
npm run dev
uv run uvicorn ...
```

---

# 47. Backend Definition of Done

A backend feature is complete when:

```text
[ ] typed input/output
[ ] domain boundary respected
[ ] failure behavior defined
[ ] unit/integration test
[ ] telemetry if relevant
[ ] no vendor leakage
[ ] no secret leakage
[ ] docs updated
[ ] challenge-critical regression not broken
```

---

# 48. Backend Release Blockers

Block release if:

- deleted knowledge remains retrievable;
- a RED deterministic decision can be downgraded;
- voice happy path is broken;
- metrics no longer reflect real events;
- citation metadata is fabricated/missing;
- challenge runtime model is not declared/compliant;
- README setup is stale;
- secrets are committed;
- official cases are hard-coded.

---

<div align="center">

## ◈ Backend Principle

**LIMEN may use probabilistic models, but its critical contracts must remain explicit, testable, and auditable.**

</div>
