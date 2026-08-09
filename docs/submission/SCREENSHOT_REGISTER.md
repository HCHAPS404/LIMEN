# Screenshot register (final report)

Do **not** fabricate images. Capture during FINAL POLISH / operator session.

| ID | Subject | Source screen | Status |
| --- | --- | --- | --- |
| S01 | Call interface listening/speaking | `/call` | `FINAL_EVIDENCE_REQUIRED:SHOT_CALL` |
| S02 | Knowledge document AVAILABLE | `/knowledge` | `FINAL_EVIDENCE_REQUIRED:SHOT_KNOWLEDGE_AVAILABLE` |
| S03 | TRAZA with evidence refs | `/trace/:callId` | `FINAL_EVIDENCE_REQUIRED:SHOT_TRAZA` |
| S04 | RED escalation / safety card | Trace or summary | `FINAL_EVIDENCE_REQUIRED:SHOT_RED` |
| S05 | Structured call summary | Sessions / summary | `FINAL_EVIDENCE_REQUIRED:SHOT_SUMMARY` |
| S06 | Provider health (challenge) | `/settings` or `/health/providers` | `FINAL_EVIDENCE_REQUIRED:SHOT_HEALTH` |
| S07 | Model selection table | Report figure from `docs/MODEL_SELECTION.md` | Optional export |
| S08 | RAG / corpus note | Report figure from generated RAG/corpus docs | Optional export |
| S09 | Architecture diagram export | Mermaid → PNG from `ARCHITECTURE.md` | `FINAL_EVIDENCE_REQUIRED:SHOT_ARCH_EXPORT` |
| S10 | Decision flow export | Mermaid → PNG from `DECISION_FLOW.md` | `FINAL_EVIDENCE_REQUIRED:SHOT_DECISION_EXPORT` |

Store final images under `docs/submission/assets/` (gitkeep only until real files exist).
