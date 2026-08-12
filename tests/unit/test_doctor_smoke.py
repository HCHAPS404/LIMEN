"""Unit tests for doctor / smoke-local helpers (no live servers required)."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _load(name: str, relative: str):
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def doctor():
    return _load("limen_doctor_under_test", "scripts/doctor.py")


@pytest.fixture(scope="module")
def smoke():
    return _load("limen_smoke_under_test", "scripts/smoke_local.py")


def test_doctor_detect_os_returns_check(doctor) -> None:
    check = doctor._detect_os()
    assert check.name == "os"
    assert check.detail
    assert check.level == "host"


def test_doctor_venv_python_resolution(doctor, tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(doctor, "ROOT", tmp_path)
    assert doctor._venv_python() is None
    unix = tmp_path / ".venv" / "bin" / "python"
    unix.parent.mkdir(parents=True)
    unix.write_text("", encoding="utf-8")
    assert doctor._venv_python() == unix


def test_smoke_get_json_parses(smoke, monkeypatch) -> None:
    class _Resp:
        status = 200

        def read(self) -> bytes:
            return json.dumps({"status": "ok", "runtime_profile": "development"}).encode()

        def __enter__(self) -> _Resp:
            return self

        def __exit__(self, *args: object) -> None:
            return None

    monkeypatch.setattr(smoke.urllib.request, "urlopen", lambda *a, **k: _Resp())
    status, payload = smoke._get_json("http://127.0.0.1:8000/health", 1.0)
    assert status == 200
    assert payload["status"] == "ok"
