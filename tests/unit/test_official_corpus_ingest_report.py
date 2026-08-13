"""Accounting for official corpus 107/107 — no live ingest."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load_ingest_script():
    path = ROOT / "scripts" / "ingest_official_corpus.py"
    spec = importlib.util.spec_from_file_location("official_corpus_ingest_under_test", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_corpus_full_closed_requires_every_discovered_file() -> None:
    closed = _load_ingest_script().corpus_full_closed
    assert closed(discovered=107, indexed=44, duplicate=63, failed=0) is True
    assert closed(discovered=107, indexed=63, duplicate=0, failed=43) is False
    assert closed(discovered=107, indexed=0, duplicate=107, failed=0) is True
    assert closed(discovered=0, indexed=0, duplicate=0, failed=0) is False
