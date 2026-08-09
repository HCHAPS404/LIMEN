# LIMEN Model Selection — PHASE 5 / 5.1

Human-maintained. Metrics below come from generated evaluation artifacts, not estimates.

## Scope

Three G3-local Ollama candidates were evaluated for LIMEN's **patient-facing
response** LLM role:

- `llama3.2:1b`
- `llama3.2:3b`
- `phi3.5`

Official dataset evaluation (PHASE 5C.2) used reconstructed conversations
`(caso_id, capa)` — **320** per model — with advisory risk labels for
**benchmarking only**.

Artifacts:

- `docs/LLM_BENCHMARK_OFFICIAL.generated.md`
- `runtime/benchmarks/llm/runs/official_20260808T181435Z/`
- Synthetic control (separate): `docs/LLM_BENCHMARK.generated.md`

## Official measured results

| Model | Macro F1 | RED recall | RED FN |
| --- | ---: | ---: | ---: |
| llama3.2:1b | 0.303 | 0.000 | 24/24 |
| llama3.2:3b | 0.197 | 0.000 | 24/24 |
| **phi3.5** | **0.445** | **0.375** | **15/24** |

Selection: **PRIMARY runtime LLM = `phi3.5`** (strongest available G3 local model
on the official advisory task).

## Architectural conclusion (critical)

These results also prove that **all three small LLMs are insufficiently reliable
as standalone RED/YELLOW/GREEN clinical classifiers**.

Therefore:

- The advisory classification benchmark **must not** become the production
  safety authority.
- **Safety Governor** + `enforce_floor` remain authoritative for
  `SafetyDecision`.
- Phi-3.5 is subordinate: it may phrase patient-facing language under trusted
  application state; it **cannot** set, downgrade, or replace final severity.
- Production safety fallback is **deterministic templates**, not
  `llama3.2:1b` / `llama3.2:3b` (both had RED recall = 0 on the official set).

This separation is an architectural strength, not a hidden limitation.

## PHASE 5.1 runtime role

Configured challenge runtime (operator opt-in):

```bash
LLM_PROVIDER=ollama
LLM_MODEL=phi3.5
LLM_BASE_URL=http://127.0.0.1:11434
LLM_TIMEOUT_S=45
```

CI / default settings remain:

```bash
LLM_PROVIDER=stub
LLM_MODEL=stub-model
```

Phi is allowed to:

- generate concise patient-facing Spanish replies;
- assist phrasing under trusted `ClinicalState`, uncertainty, and final
  `SafetyDecision`.

Phi must not:

- determine final RED/YELLOW/GREEN;
- override `SafetyDecision` / suppress escalation;
- invent evidence, citations, medications, or doses.

If Ollama is unreachable, LIMEN enters **DEGRADED_LLM_MODE**: Safety Governor,
RAG, and deterministic templates remain operational.

## Claims we do not make

- Phi-3.5 is **not** medically validated.
- Official advisory macro-F1 / RED recall are **not** voice challenge metrics.
- Secondary models are **not** clinically safer fallbacks.

## Related

- `BACKEND.md` § Runtime LLM Layer / Safety Governor
- `docs/LLM_BENCHMARK_OFFICIAL.generated.md`
