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
- [ ] Exported PNG/SVG attached to report package  
  `FINAL_EVIDENCE_REQUIRED:SHOT_ARCH_EXPORT`  
  `FINAL_EVIDENCE_REQUIRED:SHOT_DECISION_EXPORT`

## 03 Final report

- [x] Draft `docs/submission/FINAL_REPORT.md`
- [x] Phi-3.5 declared + Safety Governor authority explained
- [x] Official model-only limitations disclosed
- [x] Prompts/config appendix linked
- [x] Process / phases documented
- [ ] Screenshots inserted (`SCREENSHOT_REGISTER.md`)
- [ ] Demo video linked `FINAL_EVIDENCE_REQUIRED:DEMO_VIDEO`

## 04 Demo video + questions

- [x] Demo script `DEMO_SCRIPT.md`
- [x] Question 1 draft
- [x] Question 2 draft
- [x] Shot list `VIDEO_SHOT_LIST.md`
- [ ] Recorded video `FINAL_EVIDENCE_REQUIRED:DEMO_VIDEO`

## Gates

| Gate | Status | Evidence |
| --- | --- | --- |
| G1 | PARTIAL | Package draft; video/screenshots pending |
| G2 | PASS* | `docs/G2_BOOTSTRAP.generated.md` (293.85s); strict clone `FINAL_EVIDENCE_REQUIRED:G2_STRICT_CLONE` |
| G3 | PASS | phi3.5 / challenge profile |
| G4 | PARTIAL | `FINAL_EVIDENCE_REQUIRED:G4_P50` `FINAL_EVIDENCE_REQUIRED:G4_P95` + human mic |
| G5 | PARTIAL | `FINAL_EVIDENCE_REQUIRED:G5_UI` |

\*Host caches may have been warm during measurement.

## Metrics

| Metric | Status |
| --- | --- |
| Voice P50 | `FINAL_EVIDENCE_REQUIRED:G4_P50` |
| Voice P95 | `FINAL_EVIDENCE_REQUIRED:G4_P95` |
| Input/output tokens | Partial / often null from provider — disclose |
| LLM calls | Measured per turn when instrumented |
| RAG queries | Measured per turn when instrumented |
| Cost/call | `FINAL_EVIDENCE_REQUIRED:COST_CALL` |

## Pre-submit scans

```bash
make verify-submission-evidence
python scripts/phase9_secret_scan.py
```
