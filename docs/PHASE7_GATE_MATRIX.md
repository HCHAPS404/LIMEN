# Gate Status Matrix — PHASE 7

Evidence-based. Architecture alone is never PASS.

| Gate | Status | Evidence |
| --- | --- | --- |
| **G1 Deliverables** | PARTIAL | Repo has API, web, TRAZA, knowledge, safety, voice stack, README, ADRs. Final video/demo assets and final metrics package still deferred. |
| **G2 ≤15 min startup** | PARTIAL | `make bootstrap` + `make run-challenge` documented. Cold-start wall-clock not re-measured in PHASE 7 (`cold-start-report` may be UNMEASURED). |
| **G3 allowed model** | PASS | Primary challenge LLM = `phi3.5` via Ollama; selection artifacts in `docs/MODEL_SELECTION.md`. Profile enforces `LLM_MODEL=phi3.5`. |
| **G4 real voice** | PARTIAL | Real STT/TTS path exists (Faster-Whisper CUDA + Piper). Official browser speech-end→playback N≥20 / P50/P95 **deferred** (PHASE 6.3 debt). |
| **G5 live knowledge** | PARTIAL | Automated upload→AVAILABLE→probe→delete→forget in golden E2E + prior lifecycle tests. **Manual admin-console G5** with unique unseen fact still operator-verified. |

## Rubric coverage (analysis only — no polish)

| Rubric area | Covered now | Gaps (do not fix in PHASE 7) |
| --- | --- | --- |
| RAG / clinical / living knowledge | Hybrid RAG, E5 path, lifecycle, seed prepare | Full official corpus auto-ingest; dense calibration re-run |
| Decision / escalation | Safety Governor, enforce_floor, escalation artifact on finish | Hospital notification (out of scope) |
| Conversation design | ConversationContext, pending questions | Human conversational tuning deferred |
| Voice | Browser mic, Whisper, Piper, barge-in | Official latency samples, Piper latency |
| Video/demo | Not produced | Demo video assets |
| Repo/process | Makefile challenge targets, preflight, docs | Final submission packaging |

## Technical debt register

### BLOCKER
- None for subsystem existence. Integration blockers only if challenge preflight FALSE on target hardware.

### HIGH
- Official browser voice latency N≥20 + README P50/P95
- Manual G5 admin-console verification on challenge machine
- G2 cold-start measurement on challenge laptop

### MEDIUM
- Conversation UX repetition/endpointing human tuning
- Cost/call production-equivalent pricing source
- Full official corpus prepare path beyond seed

### POST-CHALLENGE
- Piper replacement / TTS optimization
- AudioWorklet migration
- UI visual polish
- Video assets production
