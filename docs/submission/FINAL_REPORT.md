# LIMEN — Final Report (Tech Sphere Challenge 2026)

**Status:** Draft for submission package.  
**G1:** remains PARTIAL until video + final screenshot package are attached.  
Unresolved markers: search `FINAL_EVIDENCE_REQUIRED`.

---

## 1. Executive summary

LIMEN is a browser-based postoperative follow-up agent for the Tech Sphere
Challenge 2026. It listens to patients in Spanish, maintains an explicit
clinical state, retrieves living knowledge with provenance, and escalates when
deterministic safety rules require it.

The central design choice is architectural: **language models generate and
phrase; they do not own clinical risk.** Official local-model benchmarks showed
that even the best allowed candidate (Phi-3.5) has insufficient RED recall as a
standalone classifier. LIMEN therefore keeps a **Safety Governor** as the
authoritative decision layer.

## 2. Problem

After surgery, patients need timely follow-up. Clinicians cannot call everyone
continuously. A voice agent can help triage routine recovery questions — but a
wrong “you’re fine” on a true emergency is worse than a cautious escalation.

False negatives on RED risk are more severe than false positives.

## 3. Objectives

1. Real-time browser voice conversation (G4).
2. Live knowledge upload, use, delete, and forget (G5).
3. Traceable decisions (TRAZA) and structured call summaries.
4. Reproducible local setup within challenge constraints (G2/G3).
5. Honest metrics — measured or explicitly UNMEASURED.

## 4. LIMEN concept

LIMEN = **threshold**. The system stands between patient speech and clinical
action: convert speech → structured state → evidence → safety floor → constrained
response → speech.

It is **not** a medical device and **not** a replacement for a clinician.

## 5. Architecture

Modular monolith (`ARCHITECTURE.md`). Browser UI + FastAPI API + domain packages
under `limen/`. Vendor SDKs stay inside provider adapters.

Submission diagram: [`docs/submission/ARCHITECTURE.md`](ARCHITECTURE.md).

**Local presentation layer (cold start for any clone):** progressive README
levels + [`docs/GETTING_STARTED.md`](../GETTING_STARTED.md) +
[`docs/OPERATOR_WALKTHROUGH.md`](../OPERATOR_WALKTHROUGH.md). Canonical doc
index: [`docs/README.md`](../README.md). Challenge runtime remains local
(`make run-challenge`); cloud split-hosting is not required by the architecture.

## 6. Clinical decision architecture

Pipeline:

Clinical extraction → ClinicalState (KNOWN_NORMAL / KNOWN_ABNORMAL / UNKNOWN /
CONFLICTING) → uncertainty → optional Hybrid RAG → Safety Governor floor →
`enforce_floor` → Phi or templates → validator → patient.

Principle: **`unknown != normal`**.

Diagram: [`DECISION_FLOW.md`](DECISION_FLOW.md).

## 7. RAG / living knowledge

Hybrid retrieval: multilingual-e5-small (384-d) + Qdrant cosine + SQLite FTS5 +
RRF fusion. Knowledge lifecycle supports hot upload and verified deletion.

Official corpus: **107 PDFs discovered**; smoke indexed **8** documents
(0 failed, 357 chunks). Full 107/107 verification:

`FINAL_EVIDENCE_REQUIRED:OFFICIAL_CORPUS_FULL`

Diagram: [`KNOWLEDGE_FLOW.md`](KNOWLEDGE_FLOW.md).

## 8. Voice

- STT: faster-whisper-small, CUDA, float16  
- TTS: Piper `es_MX-claude-high`  
- Browser VAD, WebSocket streaming, barge-in / stale-response protection  

Official challenge latency (speech-end → browser playback start):

| Metric | Value |
| --- | --- |
| P50 | `FINAL_EVIDENCE_REQUIRED:G4_P50` |
| P95 | `FINAL_EVIDENCE_REQUIRED:G4_P95` |

Do not substitute server TTS-ready proxies.

## 9. Conversation context

`ConversationContext` keeps a bounded recent window, answered questions, and
interrupted-intent markers so multi-turn progression participates in the next
decision without treating the LLM as long-term memory authority.

## 10. Safety

Safety Governor evaluates deterministic text/state rules and enforces a monotonic
floor. Generative output cannot weaken RED. Escalation artifacts persist on RED
finish. Injection text (patient or document) is treated as data.

## 11. Model selection

Official **model-only advisory** benchmark (320 conversations/model):

| Model | Macro F1 | RED recall | RED FN |
| --- | ---: | ---: | ---: |
| llama3.2:1b | 0.303 | 0.000 | 24/24 |
| llama3.2:3b | 0.197 | 0.000 | 24/24 |
| **phi3.5** | **0.445** | **0.375** | **15/24** |

Source: `docs/MODEL_SELECTION.md`, `docs/LLM_BENCHMARK_OFFICIAL.generated.md`.

**These figures are NOT “LIMEN RED recall”.** They motivate keeping Safety
Governor authoritative while Phi handles patient-facing language under trusted
application state.

## 12. Evaluation

| Suite | Nature | Result (truthful) |
| --- | --- | --- |
| Official LLM advisory | OFFICIAL DATASET / MODEL-ONLY | Phi selected; RED recall 0.375 |
| Challenge scenarios (PHASE 8) | STUB-ISOLATED providers, real Safety/RAG domains | 23 PASS / 0 FAIL / 25 total |
| Real Phi targeted (PHASE 9) | REAL LLM + Safety | 7/7, 0 RED FN |
| Voice browser gate | MANUAL_UNVERIFIED | G4 PARTIAL |
| G5 admin UI | MANUAL_UNVERIFIED | G5 PARTIAL |
| G2 bootstrap | Measured clean worktree (host caches may be warm) | 293.85s PASS; strict clone `FINAL_EVIDENCE_REQUIRED:G2_STRICT_CLONE` |

## 13. Observability / TRAZA

Every challenge-critical stage emits structured events. UI `/trace/:callId`
reconstructs turns with evidence refs. See [`TRAZA.md`](TRAZA.md).

## 14. Reproducibility

```bash
cp .env.example .env
make bootstrap
make prepare-voice
make prepare-llm-bench PULL=1
make prepare-knowledge
make verify-challenge-environment
make run-challenge
```

Details: `docs/CHALLENGE_RUNTIME.md`, `docs/G2_BOOTSTRAP.generated.md`.

## 15. AI-assisted development process

LIMEN was developed with AI coding assistants used for planning, scaffolding,
tests, evaluation harnesses, and documentation drafts. Humans owned architecture
boundaries, Safety Governor policy, git publish, and claim verification.

Validation emphasis:

- unit/integration/safety tests before accepting behavior changes;
- generated metrics only from evaluation scripts;
- no invented gate PASS without evidence.

Representative prompt categories: [`PROMPTS_APPENDIX.md`](PROMPTS_APPENDIX.md).

## 16. Technical decisions

**Key decision:** do not trust the LLM with final clinical risk.

| Alternative | Why rejected |
| --- | --- |
| LLM-only triage | Official RED recall ≤ 0.375; Llama variants 0.0 |
| Larger/cloud-only model | Challenge prefers local G3 path; privacy/runtime constraints |
| Small local LLM + Safety Governor | **Chosen** — language under floor; deterministic escalation |

Risks remaining: rule coverage gaps, extraction errors, FP YELLOW, voice latency.

## 17. Limitations

- Not a certified medical device; not a clinician replacement.
- Local LLM language quality is bounded.
- Official browser voice P50/P95 still UNMEASURED.
- Deterministic safety rules need broader clinical validation.
- Knowledge quality depends on corpus curation.
- Full official PDF corpus ingestion not yet verified at 107/107.
- Human clinical validation is outside hackathon scope.

## 18. Future work

Clinical validation studies; STT accent robustness; TTS latency/naturalness;
AudioWorklet; expanded rule validation; hospital integration — **after**
challenge-critical gates are closed.

## 19. Demo evidence

Script: [`DEMO_SCRIPT.md`](DEMO_SCRIPT.md).  
Shot list: [`VIDEO_SHOT_LIST.md`](VIDEO_SHOT_LIST.md).  
Actual video: `FINAL_EVIDENCE_REQUIRED:DEMO_VIDEO`  
Screenshots: [`SCREENSHOT_REGISTER.md`](SCREENSHOT_REGISTER.md)

## 20. Conclusion

LIMEN demonstrates a complete challenge runtime: voice path, living knowledge,
traceability, and a safety architecture that treats generative models as
subordinate. Remaining submission work is evidence closure (human G4/G5, video,
strict metrics) — not a redesign of the core.

---

## Appendix pointers

- Model selection: `docs/MODEL_SELECTION.md`
- Challenge eval: `runtime/evals/challenge/20260809T035544Z/`
- Gate status: `docs/PHASE9_GATE_STATUS.generated.md`
- License: MIT (`LICENSE`)
