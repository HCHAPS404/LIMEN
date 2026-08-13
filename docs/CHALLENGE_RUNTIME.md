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

**Timed (≤15 min), after host prereqs:**

```bash
cp .env.example .env
make lift
```

System prerequisites (**before** the G2 timer): Python 3.11+, Node 20+,
GNU Make, Git, Ollama running with **`phi3.5` already pulled**, NVIDIA driver/GPU
for CUDA STT (Linux/WSL). On Windows use **WSL2 + Ubuntu**. First Hugging Face
Whisper/Piper download is host setup (`make prepare-voice` once), not the clock.

`make lift` runs bootstrap, voice assets without eval fixtures, LLM check
**without** `PULL=1`, then `run-challenge` (preflight once). Do not run
`verify-challenge-environment` separately — it is already inside `run-challenge`.

Optional after the stack is up (not G2):

```bash
make prepare-knowledge
# export LIMEN_DATASET_PATH=... && make prepare-official-knowledge
make smoke-local
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
