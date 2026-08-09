# ADR-0005 — Persistence and vector strategy

## Status
Accepted (updated for PHASE 3)

## Context
`BACKEND.md` lists SQLAlchemy 2 and Qdrant as the canonical long-term stack. The
frontend already needs calls, knowledge, traces, and a voice stream. Migrating
the working `sqlite3` + cookie-auth schema to SQLAlchemy in the same pass would
delay challenge-critical surfaces without improving safety or forgetting.

PHASE 3 requires hybrid retrieval (dense + lexical) behind `EvidenceRetriever`
without redesigning PHASE 1/2 contracts.

## Decision
- Keep **raw `sqlite3`** with a versioned schema string and **WAL** mode for the
  product tables (`calls`, `documents`, `document_chunks`, FTS5, `trace_events`).
- Keep **lexical retrieval with FTS5** as one hybrid path.
- Use **Qdrant local/path mode** (`VECTOR_PATH`) for dense vectors — no Docker,
  no cloud, no external server. A process-wide singleton is required because the
  embedded client locks the storage folder.
- Expose `VectorStore` protocol with `QdrantVectorStore` (default) and
  `NullVectorStore` (escape hatch via `VECTOR_STORE_BACKEND=null`).
- Default embeddings are **stub** for CI/cold-start; optional
  `sentence-transformers` adapter (default model candidate:
  `intfloat/multilingual-e5-small`; BGE-M3 remains a heavier alternative).
- Fuse ranked lists with **RRF** in `HybridEvidenceRetriever`.

## Embedding tradeoffs (operational)
| Candidate | Dim | Approx size | Notes |
|---|---|---|---|
| stub (default CI) | configurable (64) | 0 | Deterministic unit/integration |
| multilingual-e5-small | 384 | ~120MB weights (+ CPU torch) | PHASE 3.1 validated; E5 prefixes in adapter; `dense_min_score` ≈0.795; install via CPU-first script |
| BGE-M3 | 1024 | ~2GB+ | Stronger; heavier RAM/cold-start — not the challenge baseline |

### Model resolution (PHASE 3.2)
1. `EMBEDDING_MODEL_PATH` if set and usable locally.
2. Else `EMBEDDING_MODEL` as a local directory **or** the official HF id
   (`intfloat/multilingual-e5-small`).
3. Fail clearly on load if neither resolves — no private mirrors, no machine-specific
   absolute paths in the public setup.

CPU-first install: `scripts/install_embeddings_cpu.py` (torch from
`https://download.pytorch.org/whl/cpu`). Canonical evaluator venv is `.venv`.
`.venv-embeddings` is a local sandbox workaround only and is not part of
evaluator instructions.

## Vector index compatibility
Qdrant collections are named from an **embedding fingerprint**
(`provider|model|dimensions|cosine`). Meta file `embedding_index.json` records
the active fingerprint. Switching provider/model/dimension recreates the
collection and requires knowledge re-ingest — stale vectors are never searched.

## Consequences
- AVAILABLE requires verified lexical **and** dense indexes.
- Deletion verifies zero active hits on **both** paths (ZXQ-417 forget tests).
- ConversationOrchestrator remains backend-agnostic via `EvidenceRetriever`.
- Full SQLAlchemy ORM migration remains deferred.

## Challenge impact
Does not weaken safety, provenance, or knowledge forgetting. Keeps cold-start
compatible when `EMBEDDING_PROVIDER=stub`.
