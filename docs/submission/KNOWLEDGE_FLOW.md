# Living knowledge flow (submission)

Supports G5 explanation: upload → use → delete → forget without restart.

## Ingest path

```mermaid
flowchart LR
  U[Admin upload] --> UP[UPLOADED]
  UP --> PR[PROCESSING]
  PR --> PARSE[Parse PDF/text<br/>OCR if needed]
  PARSE --> CH[Chunking]
  CH --> E5[E5 embeddings]
  CH --> LEX[FTS5 lexical index]
  E5 --> QD[Qdrant dense index]
  LEX --> AV[AVAILABLE]
  QD --> AV
  AV --> RET[Hybrid retrieve + provenance]
```

## Delete / forget path

```mermaid
flowchart LR
  D[Admin delete] --> RM[REMOVING]
  RM --> PURGE[Purge FTS5 + Qdrant chunks]
  PURGE --> VER[Verification probe]
  VER --> REM[REMOVED]
  REM --> NONE[Same query returns no deleted chunks]
```

## Truthful corpus status

| Item | Status |
| --- | --- |
| Official PDFs discovered | **107** (`docs/OFFICIAL_CORPUS.generated.md`) |
| Indexed AVAILABLE | **107 / 107** (direct ingest; API stopped) |
| Full 107/107 ingestion | **yes** |

Live G5 human admin-console confirmation: **PASS** (2026-08-09 operator UI + generated evidence)


## Code

- Ingestion: `limen/knowledge/ingestion.py`
- Deletion: `limen/knowledge/deletion.py`
- Hybrid RAG: `limen/knowledge/hybrid.py`
- Admin UI: `apps/web/src/pages/Knowledge/KnowledgePage.tsx`
