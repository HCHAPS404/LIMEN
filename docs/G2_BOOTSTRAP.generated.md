# G2 Bootstrap Evidence (generated)

Generated: 2026-08-09T04:09:35.861458+00:00
Machine: `archlinux` (Linux-7.1.6-arch1-1-x86_64-with-glibc2.44)
Total: **293.85s** (4.9 min)
≤15 min: **True**
READY_FOR_CHALLENGE_RUNTIME: **True**
G2 status: **PASS**

## System prerequisites (before timer)

- Python 3.11+
- Node.js 20+ / npm
- Ollama installed and running (phi3.5)
- NVIDIA driver + CUDA GPU for STT_DEVICE=cuda
- Network for pip/npm/HF/Ollama when assets uncached

## Start conditions

```json
{
  "fresh_worktree": true,
  "no_venv": true,
  "no_node_modules": true,
  "no_runtime_db": true,
  "source_ref": "9fa4b8f56cb45336d86fe47d7aaa63c22df9b301",
  "note": "Measured from current working tree (excludes .venv/node_modules/runtime). Host pip/npm/ollama/HF caches may still be warm. Official jury clone requires these files to be committed.",
  "source": "working_tree_rsync"
}
```

## Commands / stages

- `sync_working_tree`: 39.46s ok=True — `rsync -a --delete --exclude .venv/ --exclude apps/web/node_modules/ --exclude runtime/ --exclude .tmp/ --exclude .cache/ --exclude .git/ /home/hell/Projects/LIMEN/ /home/hell/Projects/limen-g2-bootstrap-20260809T040935Z/`
- `copy_env`: 0.01s ok=True — `cp .env.example .env`
- `make_bootstrap`: 115.29s ok=True — `make bootstrap`
- `make_prepare_voice`: 88.61s ok=True — `make prepare-voice`
- `make_prepare_llm`: 1.33s ok=True — `make prepare-llm-bench PULL=1`
- `make_prepare_knowledge`: 0.39s ok=True — `make prepare-knowledge`
- `verify_challenge_environment`: 48.61s ok=True — `make verify-challenge-environment`
- `run_challenge_health`: 0.13s ok=True — `make run-challenge`

## URLs

- API health: http://127.0.0.1:8000/health
- Web: http://127.0.0.1:5173

## Health result

```json
{
  "status": "ok",
  "version": "0.1.0",
  "app_env": "development",
  "llm_provider": "ollama",
  "llm_model": "phi3.5",
  "degraded_llm_mode": false,
  "database": {
    "database": "ok",
    "schema_version": "5",
    "path": "runtime/db/limen.db"
  }
}
```

Machine-readable: `/home/hell/Projects/LIMEN/runtime/evals/g2/latest.json`
