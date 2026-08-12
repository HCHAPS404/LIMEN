.PHONY: bootstrap run dev-api dev-web lint typecheck test verify format help \
	doctor smoke-local \
	verify-rag-real verify-rag-stub install-embeddings-cpu cold-start-report \
	verify-llm-environment prepare-llm-bench verify-llm-bench \
	verify-official-dataset verify-llm-bench-official \
	prepare-voice verify-voice-environment verify-voice verify-voice-real \
	dev-api-voice \
	prepare-knowledge prepare-official-knowledge measure-g2-bootstrap \
	verify-challenge-environment run-challenge verify-phase7 \
	verify-challenge-eval verify-submission-evidence

# Cross-platform venv paths: Linux/macOS/WSL → .venv/bin; native Windows → .venv/Scripts
ifeq ($(OS),Windows_NT)
  PYTHON ?= .venv/Scripts/python.exe
  PIP ?= .venv/Scripts/pip.exe
  UV_BIN ?= .venv/Scripts/uv.exe
  # Windows host interpreter for creating the venv (Git Bash / Make).
  HOST_PYTHON ?= py -3
else
  PYTHON ?= .venv/bin/python
  PIP ?= .venv/bin/pip
  UV_BIN ?= .venv/bin/uv
  HOST_PYTHON ?= python3
endif

# Prefer project venv; fall back so `make doctor` works on a cold clone.
RUN_PY = $(shell \
	if [ -f .venv/bin/python ]; then echo .venv/bin/python; \
	elif [ -f .venv/Scripts/python.exe ]; then echo .venv/Scripts/python.exe; \
	elif command -v python3 >/dev/null 2>&1; then echo python3; \
	elif command -v python >/dev/null 2>&1; then echo python; \
	else echo python3; fi)

UV ?= $(shell if [ -x "$(UV_BIN)" ]; then echo $(UV_BIN); elif command -v uv >/dev/null 2>&1; then command -v uv; else echo uv; fi)
NPM ?= npm
TMPDIR_LOCAL ?= $(CURDIR)/.tmp
# Opt-in: INSTALL_EMBEDDINGS=0 skips CPU torch + sentence-transformers during bootstrap.
INSTALL_EMBEDDINGS ?= 1
INGEST ?= 0
# Optional local E5 checkout (relative project cache). Hub id used when unset.
EMBEDDING_MODEL_PATH ?= $(shell \
	if [ -f $(CURDIR)/.cache/models/multilingual-e5-small/model.safetensors ]; then \
		echo $(CURDIR)/.cache/models/multilingual-e5-small; \
	elif [ -f $(CURDIR)/runtime/models/multilingual-e5-small/model.safetensors ]; then \
		echo $(CURDIR)/runtime/models/multilingual-e5-small; \
	fi)

help:
	@echo "LIMEN — progressive paths:"
	@echo "  Level 1 stubs:   make doctor && make bootstrap && make run  (+ make dev-web)"
	@echo "                   make smoke-local"
	@echo "  Level 3 challenge: make prepare-voice prepare-llm-bench prepare-knowledge"
	@echo "                     make verify-challenge-environment && make run-challenge"
	@echo "  OS: Linux, macOS, Windows via WSL2 (native Windows = best-effort / Git Bash)"
	@echo ""
	@echo "LIMEN targets:"
	@echo "  make doctor                 - cross-platform readiness (READY_STUBS / challenge hint)"
	@echo "  make smoke-local            - HTTP smoke vs running API (:8000) + web (:5173)"
	@echo "  make bootstrap              - create .venv, install deps (CPU embeddings by default)"
	@echo "  make run                    - alias for make dev-api"
	@echo "  make run-challenge          - PHASE 7 challenge runtime (API+web, real stack)"
	@echo "  make verify-challenge-environment - READY_FOR_CHALLENGE_RUNTIME preflight"
	@echo "  make prepare-knowledge      - deterministic seed corpus (INGEST=1 optional)"
	@echo "  make prepare-official-knowledge - ingest official PDFs (LIMEN_DATASET_PATH)"
	@echo "  make measure-g2-bootstrap   - clean worktree G2 timing → docs/G2_BOOTSTRAP.generated.md"
	@echo "  make verify-phase7          - golden full-system integration (stub CI path)"
	@echo "  make verify-challenge-eval  - PHASE 8 challenge evaluation suite + artifacts"
	@echo "  make verify-submission-evidence - scan FINAL_EVIDENCE_REQUIRED placeholders"
	@echo "  make verify                 - full quality gate (STUB embeddings in tests)"
	@echo "  make verify-rag-stub        - deterministic RAG eval (stub)"
	@echo "  make verify-rag-real        - real multilingual-e5-small validation (opt-in)"
	@echo "  make verify-llm-environment - PHASE 5B Ollama/G3 preflight (no downloads)"
	@echo "  make prepare-llm-bench      - show/opt-in pull G3 models (PULL=1 to download)"
	@echo "  make verify-llm-bench       - PHASE 5C serial G3 benchmark + artifacts"
	@echo "  make verify-official-dataset - PHASE 5C.2 official dataset dry-run (no LLM)"
	@echo "  make verify-llm-bench-official - PHASE 5C.2 official advisory benchmark"
	@echo "  make prepare-voice          - install voice extras + Piper/Whisper assets + fixtures"
	@echo "  make verify-voice-environment - real STT/TTS/Ollama/Phi preflight"
	@echo "  make verify-voice           - PHASE 6 stub voice unit/integration"
	@echo "  make verify-voice-real      - PHASE 6.1/6.2 real STT/TTS tests + fixture bench"
	@echo "  make dev-api-voice          - API with CUDA12 pip libs on LD_LIBRARY_PATH"
	@echo "  make install-embeddings-cpu - CPU-first torch + sentence-transformers"
	@echo "  make cold-start-report      - print measured/UNMEASURED cold-start phases"

doctor:
	$(RUN_PY) scripts/doctor.py

smoke-local:
	$(RUN_PY) scripts/smoke_local.py $(ARGS)

bootstrap:
	@if [ ! -d .venv ]; then \
		if command -v python3 >/dev/null 2>&1; then python3 -m venv .venv; \
		elif command -v py >/dev/null 2>&1; then py -3 -m venv .venv; \
		else python -m venv .venv; fi; \
	fi
	$(PIP) install -U pip
	$(PIP) install -e ".[dev]"
	@if [ "$(INSTALL_EMBEDDINGS)" = "1" ]; then \
		$(PYTHON) scripts/install_embeddings_cpu.py; \
	else \
		echo "Skipping embeddings install (INSTALL_EMBEDDINGS=0)"; \
	fi
	@if command -v uv >/dev/null 2>&1 || [ -x "$(UV_BIN)" ]; then \
		$(UV) pip install -e ".[dev]" || true; \
		$(UV) lock 2>/dev/null || true; \
	fi
	$(PYTHON) scripts/bootstrap.py
	cd apps/web && $(NPM) install

install-embeddings-cpu:
	@if [ ! -d .venv ]; then \
		if command -v python3 >/dev/null 2>&1; then python3 -m venv .venv; \
		elif command -v py >/dev/null 2>&1; then py -3 -m venv .venv; \
		else python -m venv .venv; fi; \
	fi
	$(PYTHON) scripts/install_embeddings_cpu.py

run: dev-api

dev-api:
	$(PYTHON) -m uvicorn apps.api.main:app --reload --host 127.0.0.1 --port 8000

dev-web:
	cd apps/web && $(NPM) run dev

lint:
	$(PYTHON) -m ruff check limen apps/api tests scripts evals
	$(PYTHON) -m ruff format --check limen apps/api tests scripts evals
	@if [ -f apps/web/package.json ]; then cd apps/web && $(NPM) run lint; fi

format:
	$(PYTHON) -m ruff check --fix limen apps/api tests scripts evals
	$(PYTHON) -m ruff format limen apps/api tests scripts evals

typecheck:
	$(PYTHON) -m mypy limen apps/api
	@if [ -f apps/web/package.json ]; then cd apps/web && $(NPM) run typecheck; fi

test:
	mkdir -p $(TMPDIR_LOCAL)
	TMPDIR=$(TMPDIR_LOCAL) $(PYTHON) -m pytest -m "not real_embeddings and not real_llm"
	@if [ -f apps/web/package.json ]; then cd apps/web && $(NPM) run test; fi

verify: lint typecheck test
	$(PYTHON) scripts/check_boundaries.py
	$(PYTHON) scripts/verify_environment.py
	$(PYTHON) scripts/verify_submission.py
	@if [ -f apps/web/package.json ]; then cd apps/web && $(NPM) run build; fi

verify-rag-stub:
	mkdir -p $(TMPDIR_LOCAL)
	TMPDIR=$(TMPDIR_LOCAL) $(PYTHON) evals/rag_eval.py --provider stub
	TMPDIR=$(TMPDIR_LOCAL) $(PYTHON) evals/knowledge_lifecycle_eval.py --provider stub

verify-rag-real:
	@echo "Real E5 validation using canonical $(PYTHON)"
	@echo "Requires CPU-first embeddings from bootstrap / install-embeddings-cpu"
	@if [ -n "$(EMBEDDING_MODEL_PATH)" ]; then echo "Using EMBEDDING_MODEL_PATH=$(EMBEDDING_MODEL_PATH)"; else echo "Using Hugging Face model id (set EMBEDDING_MODEL_PATH for offline)"; fi
	mkdir -p $(TMPDIR_LOCAL) $(CURDIR)/.cache/huggingface
	$(PYTHON) scripts/install_embeddings_cpu.py
	LIMEN_REAL_EMBEDDINGS=1 TMPDIR=$(TMPDIR_LOCAL) HF_HOME=$(CURDIR)/.cache/huggingface \
		EMBEDDING_MODEL_PATH="$(EMBEDDING_MODEL_PATH)" \
		$(PYTHON) evals/calibrate_dense_scores.py
	LIMEN_REAL_EMBEDDINGS=1 TMPDIR=$(TMPDIR_LOCAL) HF_HOME=$(CURDIR)/.cache/huggingface \
		EMBEDDING_MODEL_PATH="$(EMBEDDING_MODEL_PATH)" \
		$(PYTHON) evals/rag_eval.py --provider real
	LIMEN_REAL_EMBEDDINGS=1 TMPDIR=$(TMPDIR_LOCAL) HF_HOME=$(CURDIR)/.cache/huggingface \
		EMBEDDING_MODEL_PATH="$(EMBEDDING_MODEL_PATH)" \
		$(PYTHON) evals/knowledge_lifecycle_eval.py --provider real
	LIMEN_REAL_EMBEDDINGS=1 TMPDIR=$(TMPDIR_LOCAL) HF_HOME=$(CURDIR)/.cache/huggingface \
		EMBEDDING_MODEL_PATH="$(EMBEDDING_MODEL_PATH)" \
		$(PYTHON) -m pytest tests/integration/test_real_embeddings.py -m real_embeddings -q

cold-start-report:
	$(PYTHON) scripts/report_cold_start.py

# Opt-in: PULL=1 downloads missing G3 candidates only (never during bootstrap).
PULL ?= 0

verify-llm-environment:
	@echo "PHASE 5B Ollama preflight (no sudo, no auto-pull)"
	$(PYTHON) scripts/verify_llm_environment.py

prepare-llm-bench:
	@echo "PHASE 5B prepare G3 models (llama3.2:1b / llama3.2:3b / phi3.5)"
	@if [ "$(PULL)" = "1" ]; then \
		$(PYTHON) scripts/prepare_llm_bench.py --pull; \
	else \
		$(PYTHON) scripts/prepare_llm_bench.py; \
	fi

verify-llm-bench:
	@echo "PHASE 5C G3 local Ollama benchmark (serial: llama3.2:1b / llama3.2:3b / phi3.5)"
	mkdir -p $(CURDIR)/runtime/benchmarks/llm $(CURDIR)/runtime/benchmarks/llm/runs
	$(PYTHON) scripts/verify_llm_environment.py || true
	$(PYTHON) evals/llm/benchmark.py --all-allowed-local --write-docs

verify-official-dataset:
	@echo "PHASE 5C.2 official dataset dry-run (no LLM calls)"
	mkdir -p $(CURDIR)/runtime/benchmarks/llm
	$(PYTHON) scripts/verify_official_dataset.py

verify-llm-bench-official:
	@echo "PHASE 5C.2 official advisory benchmark (serial G3 models)"
	mkdir -p $(CURDIR)/runtime/benchmarks/llm $(CURDIR)/runtime/benchmarks/llm/runs
	$(PYTHON) scripts/verify_official_dataset.py
	$(PYTHON) evals/llm/official_benchmark.py --write-docs

verify-voice:
	@echo "PHASE 6 voice unit/integration (stub STT/TTS; no model download)"
	$(PYTHON) -m pytest tests/unit/test_voice_phase6.py tests/unit/test_voice_timing_phase62.py \
		tests/integration/test_voice_ws_phase6.py -q

prepare-voice:
	@echo "PHASE 6.1/6.2 prepare voice extras + CUDA12 libs + Piper/Whisper + fixtures"
	$(PIP) install -e ".[voice]"
	$(PYTHON) scripts/prepare_voice.py
	$(PYTHON) scripts/generate_voice_fixtures.py

verify-voice-environment:
	@echo "PHASE 6.2 real voice environment preflight (CUDA preferred)"
	STT_DEVICE=$${STT_DEVICE:-cuda} $(PYTHON) scripts/verify_voice_environment.py

dev-api-voice:
	@echo "API with CUDA 12 pip libs for faster-whisper (does not downgrade system CUDA)"
	$(PYTHON) scripts/run_voice_api.py

verify-voice-real: verify-voice-environment
	@echo "PHASE 6.2 real STT/TTS tests (requires prepare-voice + CUDA12 libs)"
	LIMEN_REAL_VOICE=1 STT_PROVIDER=faster_whisper STT_DEVICE=$${STT_DEVICE:-cuda} \
		TTS_PROVIDER=piper TTS_MODEL_PATH=$(CURDIR)/runtime/models/piper \
		STT_MODEL=Systran/faster-whisper-small TTS_VOICE=es_MX-claude-high \
		$(PYTHON) -m pytest tests/integration/test_real_voice.py -m real_voice -q
	LIMEN_REAL_VOICE=1 STT_PROVIDER=faster_whisper STT_DEVICE=$${STT_DEVICE:-cuda} \
		TTS_PROVIDER=piper TTS_MODEL_PATH=$(CURDIR)/runtime/models/piper \
		LLM_PROVIDER=ollama LLM_MODEL=phi3.5 EMBEDDING_PROVIDER=stub \
		$(PYTHON) evals/voice_benchmark.py --repeats 2 --write-docs

prepare-knowledge:
	@echo "PHASE 7 deterministic knowledge seed (not full official corpus)"
	@if [ "$(INGEST)" = "1" ]; then \
		$(PYTHON) scripts/prepare_knowledge.py --ingest; \
	else \
		$(PYTHON) scripts/prepare_knowledge.py; \
	fi

# Requires LIMEN_DATASET_PATH (or ./dataset / ./data/challenge). Uses challenge profile.
LIMIT ?=
prepare-official-knowledge:
	@echo "PHASE 9 official clinical PDF corpus via existing knowledge lifecycle"
	@if [ -z "$$LIMEN_DATASET_PATH" ] && [ ! -d dataset ] && [ ! -d data/challenge ]; then \
		echo "Set LIMEN_DATASET_PATH to the official dataset root (contains textos/*.pdf)"; \
		exit 1; \
	fi
	LIMEN_RUNTIME_PROFILE=challenge $(PYTHON) scripts/ingest_official_corpus.py --ingest --smoke --write-docs \
		$(if $(LIMIT),--limit $(LIMIT),)

measure-g2-bootstrap:
	@echo "PHASE 9 G2 clean worktree bootstrap measurement"
	$(PYTHON) scripts/measure_g2_bootstrap.py $(ARGS)

verify-challenge-environment:
	@echo "PHASE 7 challenge runtime preflight (no stubs allowed)"
	LIMEN_RUNTIME_PROFILE=challenge $(PYTHON) scripts/verify_challenge_environment.py

run-challenge:
	@echo "PHASE 7 challenge runtime — API + frontend"
	@echo "Preflight: make verify-challenge-environment"
	LIMEN_RUNTIME_PROFILE=challenge $(PYTHON) scripts/run_challenge.py

verify-phase7:
	@echo "PHASE 7 golden full-system integration (stub CI path)"
	mkdir -p $(TMPDIR_LOCAL)
	TMPDIR=$(TMPDIR_LOCAL) $(PYTHON) -m pytest tests/integration/test_phase7_golden_e2e.py -q

verify-challenge-eval:
	@echo "PHASE 8 challenge evaluation & adversarial simulation"
	mkdir -p $(CURDIR)/runtime/evals/challenge $(TMPDIR_LOCAL)
	TMPDIR=$(TMPDIR_LOCAL) $(PYTHON) -m evals.challenge

verify-submission-evidence:
	@echo "PHASE 10 submission evidence placeholders (non-strict CI)"
	$(PYTHON) scripts/verify_submission_evidence.py
	$(PYTHON) scripts/verify_submission_architecture.py
	$(PYTHON) scripts/phase9_secret_scan.py || true
