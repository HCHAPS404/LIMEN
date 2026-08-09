# Challenge Runtime — PHASE 7 / PHASE 9

Single coherent LIMEN runtime for Tech Sphere Challenge 2026.

## Profile

```bash
export LIMEN_RUNTIME_PROFILE=challenge
```

This applies real-provider defaults (setdefault; explicit env wins):

| Component | Challenge value |
| --- | --- |
| LLM | `ollama` / `phi3.5` |
| STT | `faster_whisper` / CUDA / float16 |
| TTS | `piper` / `es_MX-claude-high` |
| Embeddings | `sentence-transformers` / multilingual-e5-small |
| Vectors | local Qdrant |
| Lexical | FTS5 |
| RAG | HybridEvidenceRetriever |

CI/development keep stubs. Stubs under challenge profile fail readiness.

## One evaluator path (G2)

System prerequisites (install **before** the timer): Python 3.11+, Node 20+,
Ollama running, NVIDIA driver/GPU for CUDA STT, network for first-time pulls.

```bash
cp .env.example .env
# optional official corpus:
# export LIMEN_DATASET_PATH=/absolute/path/to/official/dataset

make bootstrap
make prepare-voice                 # Whisper + Piper (HF download, deterministic)
make prepare-llm-bench PULL=1      # ollama pull phi3.5
make prepare-knowledge             # deterministic seed doc
# optional full clinical PDFs:
# make prepare-official-knowledge
make verify-challenge-environment  # READY_FOR_CHALLENGE_RUNTIME=TRUE/FALSE
make run-challenge                 # API + Vite with challenge profile
```

Clean-worktree measurement:

```bash
make measure-g2-bootstrap
# → docs/G2_BOOTSTRAP.generated.md
```

No manual `LD_LIBRARY_PATH`, no manual model file copies — `scripts/run_voice_api.py`
sets CUDA pip libs when launching the API.

## Knowledge

| Path | Command |
| --- | --- |
| Deterministic seed | `make prepare-knowledge` / `INGEST=1` |
| Official 107 PDFs | `LIMEN_DATASET_PATH=... make prepare-official-knowledge` |
| Live G5 | Admin console `/knowledge` upload → AVAILABLE → retrieve → delete → forget |

## Health

- `GET /health` — `runtime_profile`, `stub_providers`
- `GET /health/ready` — challenge stubs are hard errors
- `GET /health/providers` — LLM/STT/TTS/embeddings/vector_store

## Gate evidence docs

- G2: `docs/G2_BOOTSTRAP.generated.md`
- G4: `docs/G4_VOICE_GATE.generated.md`
- G5: `docs/G5_LIVE_KNOWLEDGE.generated.md`
- Matrix: `docs/PHASE9_GATE_STATUS.generated.md`
