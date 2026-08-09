# Evaluations

Reproducible challenge evaluations live here.

## RAG (PHASE 3 / 3.1 / 3.2)

| Command | Embeddings | Purpose |
|---|---|---|
| `make verify-rag-stub` | **STUB** (deterministic CI) | Hit@K, MRR, forget, no-evidence |
| `make verify-rag-real` | **REAL** `intfloat/multilingual-e5-small` | Cross-lingual + calibration + lifecycle |
| `evals/calibrate_dense_scores.py` | REAL E5 | Score distributions → `dense_min_score` |

```bash
# CI / default (stub only — does not download E5)
.venv/bin/python evals/rag_eval.py --provider stub
.venv/bin/python evals/knowledge_lifecycle_eval.py --provider stub

# Real model (opt-in)
make verify-rag-real
```

## LLM benchmark (PHASE 5B)

G3-allowed **local** candidates only: `llama3.2:1b`, `llama3.2:3b`, `phi3.5`.

Operator workflow:

```bash
make verify-llm-environment   # preflight (no downloads, no sudo)
make prepare-llm-bench        # list missing; PULL=1 to ollama pull the three only
make prepare-llm-bench PULL=1
make verify-llm-bench         # serial fair benchmark + artifacts
```

Artifacts:
- `runtime/benchmarks/llm/latest.json`
- `runtime/benchmarks/llm/runs/<timestamp>/{manifest,summary,*model*.json}`
- `docs/LLM_BENCHMARK.generated.md`

Official dataset resolution (no `$HOME` recursion):

1. `LIMEN_DATASET_PATH`
2. `./dataset/`
3. `./data/challenge/`
4. unavailable

When present, the report includes dataset fingerprints (filename, SHA256, rows, columns).

CI does **not** download LLMs (`real_llm` marker). Bootstrap never pulls
benchmark models. Production default stays `LLM_PROVIDER=stub` until PHASE 5.1.

## Cold-start phases

```bash
python scripts/report_cold_start.py
```

## Other

- `knowledge_lifecycle_eval.py` — ingest → retrieve → delete → prove forgetting

Stubs / Planned:

- `triage_eval.py`
- `conversation_replay.py`
- `adversarial_eval.py`
- `latency_benchmark.py`
