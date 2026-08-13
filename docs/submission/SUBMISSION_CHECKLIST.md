# Submission checklist — Tech Sphere Challenge 2026

## 01 Public repository

- [x] Public repo URL declared in README
- [x] MIT `LICENSE`
- [x] Root `README.md` competition-oriented
- [x] `.env.example` without secrets
- [x] `.gitignore` excludes `.env`, `.venv`, `node_modules`, `runtime/`, models
- [ ] Human confirms remote is up to date with submission branch  
  `FINAL_EVIDENCE_REQUIRED:PUBLIC_REPO_PUSH`

## 02 Diagrams

- [x] Architecture Mermaid — `docs/submission/ARCHITECTURE.md`
- [x] Decision flow — `docs/submission/DECISION_FLOW.md`
- [x] Knowledge flow — `docs/submission/KNOWLEDGE_FLOW.md`
- [x] TRAZA explanation — `docs/submission/TRAZA.md`
- [x] Exported PNG/SVG attached to report package  
  `docs/submission/assets/architecture.png`  
  `docs/submission/assets/decision_flow.png`

## 03 Final report

- [x] Draft `docs/submission/FINAL_REPORT.md`
- [x] Phi-3.5 declared + Safety Governor authority explained
- [x] Official model-only limitations disclosed
- [x] Prompts/config appendix linked
- [x] Process / phases documented
- [x] Screenshots inserted (`SCREENSHOT_REGISTER.md`) — S01–S06
- [x] Demo video linked — **https://youtu.be/CAO7SUBaV2s**

## 04 Demo video + questions

- [x] Demo script `DEMO_SCRIPT.md`
- [x] Question 1 draft
- [x] Question 2 draft
- [x] Shot list `VIDEO_SHOT_LIST.md`
- [x] Recorded video — **https://youtu.be/CAO7SUBaV2s**

## Gates

| Gate | Status | Evidence |
| --- | --- | --- |
| G1 | PASS | Video **https://youtu.be/CAO7SUBaV2s**; package in `docs/submission/` |
| G2 | PASS | `docs/G2_BOOTSTRAP.generated.md` (**290.52s**, git worktree HEAD, caches pip/npm/HF aisladas) |
| G3 | PASS | phi3.5 / challenge profile |
| G4 | PASS WITH WARNINGS | Operator browser 2026-08-09; warm P50/P95 **6457 / 19103 ms** (N=84) in `docs/G4_VOICE_GATE.generated.md`; barge-in subsequent PARTIAL |
| G5 | PASS | Operator UI confirm 2026-08-09 (LUNA-73 / ZXQ-921) + `docs/G5_LIVE_KNOWLEDGE.generated.md` |

\*Host Python/Node/Ollama phi3.5/NVIDIA are prerequisites; project pip/npm/HF caches were isolated in the 290.52s run.

## Metrics

| Metric | Status |
| --- | --- |
| Voice P50 | **6457 ms** (warm N=84) — `docs/G4_VOICE_GATE.generated.md` |
| Voice P95 | **19103 ms** (warm N=84) — `docs/G4_VOICE_GATE.generated.md` |
| Input/output tokens | **204476 / 17593** (137 turns, 55 calls) — `docs/EVAL_RESULTS.generated.md` |
| LLM calls | 189 |
| RAG queries | 56 |
| Cost/call | Local **$0** measured; equivalent GPT-4o mini **$0.00075** — `docs/COST_CALL.generated.md` |

## Pre-submit scans

```bash
make verify-submission-evidence
python scripts/phase9_secret_scan.py
```
