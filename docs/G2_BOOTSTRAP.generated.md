# G2 Bootstrap Evidence (generated)

Generated: 2026-08-13T04:15:46.582584+00:00
Machine: `archlinux` (Linux-7.1.6-arch1-1-x86_64-with-glibc2.44)
Total: **290.52s** (4.84 min)
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
  "source_ref": "ba80a1fe7b9a58de586505a00b8860e282a5a111",
  "strict_clone": true,
  "isolated_caches": [
    "pip",
    "npm",
    "huggingface",
    "xdg"
  ],
  "host_prereqs_not_timed": [
    "python3",
    "node/npm",
    "ollama + phi3.5 already pulled",
    "nvidia driver + CUDA GPU"
  ],
  "note": "Strict clone: git worktree from HEAD; pip/npm/HF caches empty in the worktree. Ollama weights and system interpreters are host prerequisites (not timed)."
}
```

## Commands / stages

- `git_worktree`: 0.06s ok=True — `git worktree add --detach /home/hell/Projects/limen-g2-bootstrap-20260813T041546Z HEAD`
- `copy_env`: 0.01s ok=True — `cp .env.example .env`
- `make_bootstrap`: 135.33s ok=True — `make bootstrap`
- `make_prepare_voice`: 80.04s ok=True — `make prepare-voice SKIP_FIXTURES=1`
- `make_prepare_llm`: 0.97s ok=True — `make prepare-llm-bench`
- `run_challenge_health`: 44.11s ok=True — `make run-challenge`

## URLs

- API health: http://127.0.0.1:8000/health
- Web: http://127.0.0.1:5173

## Health result

```json
{
  "status": "ok",
  "version": "0.1.0",
  "app_env": "challenge",
  "runtime_profile": "challenge",
  "llm_provider": "ollama",
  "llm_model": "phi3.5",
  "degraded_llm_mode": false,
  "stub_providers": [],
  "database": {
    "database": "ok",
    "schema_version": "5",
    "path": "/home/hell/Projects/limen-g2-bootstrap-20260813T041546Z/runtime/db/limen.db"
  }
}
```

Machine-readable: `/home/hell/Projects/LIMEN/runtime/evals/g2/latest.json`
