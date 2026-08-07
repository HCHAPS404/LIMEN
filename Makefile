.PHONY: bootstrap dev-api dev-web lint typecheck test verify format help

PYTHON ?= .venv/bin/python
UV ?= $(shell if [ -x .venv/bin/uv ]; then echo .venv/bin/uv; elif command -v uv >/dev/null 2>&1; then command -v uv; else echo uv; fi)
PIP ?= .venv/bin/pip
NPM ?= npm

help:
	@echo "LIMEN targets:"
	@echo "  make bootstrap  - create venv, install deps, init runtime"
	@echo "  make dev-api    - run FastAPI on :8000"
	@echo "  make dev-web    - run Vite on :5173"
	@echo "  make lint       - ruff + frontend lint"
	@echo "  make typecheck  - mypy + frontend typecheck"
	@echo "  make test       - pytest + frontend tests"
	@echo "  make verify     - full quality gate"

bootstrap:
	@if [ ! -d .venv ]; then python3 -m venv .venv; fi
	$(PIP) install -U pip
	$(PIP) install -e ".[dev]"
	@if command -v uv >/dev/null 2>&1 || [ -x .venv/bin/uv ]; then \
		$(UV) pip install -e ".[dev]" || true; \
		$(UV) lock 2>/dev/null || true; \
	fi
	$(PYTHON) scripts/bootstrap.py
	cd apps/web && $(NPM) install

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
	$(PYTHON) -m pytest
	@if [ -f apps/web/package.json ]; then cd apps/web && $(NPM) run test; fi

verify: lint typecheck test
	$(PYTHON) scripts/check_boundaries.py
	$(PYTHON) scripts/verify_environment.py
	$(PYTHON) scripts/verify_submission.py
	@if [ -f apps/web/package.json ]; then cd apps/web && $(NPM) run build; fi
