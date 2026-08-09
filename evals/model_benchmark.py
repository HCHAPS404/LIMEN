#!/usr/bin/env python3
"""Compatibility entrypoint — delegates to evals/llm/benchmark.py."""

from __future__ import annotations

from evals.llm.benchmark import main

if __name__ == "__main__":
    raise SystemExit(main())
