#!/usr/bin/env python3
"""Start LIMEN challenge runtime (API + Vite frontend).

Usage:
  LIMEN_RUNTIME_PROFILE=challenge python scripts/run_challenge.py

Or: make run-challenge

Requires ``make verify-challenge-environment`` to pass for a full stack.
This launcher still starts processes but exits non-zero if preflight fails,
unless ``--force`` is passed.
"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("LIMEN_RUNTIME_PROFILE", "challenge")


def _preflight() -> int:
    return subprocess.call(
        [sys.executable, str(ROOT / "scripts" / "verify_challenge_environment.py")],
        cwd=str(ROOT),
        env=os.environ.copy(),
    )


def _wait_http(url: str, timeout_s: float = 60.0) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:  # noqa: S310
                if resp.status < 500:
                    return True
        except (urllib.error.URLError, TimeoutError, OSError):
            time.sleep(0.5)
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Run LIMEN challenge runtime")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Start even if verify-challenge-environment fails",
    )
    parser.add_argument("--api-only", action="store_true")
    parser.add_argument("--skip-preflight", action="store_true")
    args = parser.parse_args()

    from limen.config.challenge_profile import apply_runtime_profile

    apply_runtime_profile()

    if not args.skip_preflight:
        code = _preflight()
        if code != 0 and not args.force:
            print(
                "Challenge preflight failed. Fix READY_FOR_CHALLENGE_RUNTIME "
                "or pass --force to start anyway.",
                file=sys.stderr,
            )
            return code

    env = os.environ.copy()
    env["LIMEN_RUNTIME_PROFILE"] = "challenge"
    python = str(ROOT / ".venv" / "bin" / "python")
    if not Path(python).is_file():
        python = sys.executable

    procs: list[subprocess.Popen[bytes]] = []

    def _shutdown(*_args: object) -> None:
        for proc in procs:
            if proc.poll() is None:
                proc.send_signal(signal.SIGTERM)
        for proc in procs:
            try:
                proc.wait(timeout=8)
            except subprocess.TimeoutExpired:
                proc.kill()

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    # API via CUDA-aware launcher when available.
    api_script = ROOT / "scripts" / "run_voice_api.py"
    api_cmd = (
        [python, str(api_script)]
        if api_script.is_file()
        else [
            python,
            "-m",
            "uvicorn",
            "apps.api.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ]
    )
    print("Starting challenge API on http://127.0.0.1:8000 …")
    procs.append(subprocess.Popen(api_cmd, cwd=str(ROOT), env=env))

    if not _wait_http("http://127.0.0.1:8000/health", timeout_s=90.0):
        print("API health check timed out.", file=sys.stderr)
        _shutdown()
        return 1
    print("API healthy.")

    if not args.api_only:
        web_dir = ROOT / "apps" / "web"
        print("Starting Vite frontend on http://127.0.0.1:5173 …")
        procs.append(
            subprocess.Popen(
                ["npm", "run", "dev", "--", "--host", "127.0.0.1", "--port", "5173"],
                cwd=str(web_dir),
                env=env,
            )
        )
        if not _wait_http("http://127.0.0.1:5173/", timeout_s=60.0):
            print(
                "Frontend did not become ready (check npm). API is still up.",
                file=sys.stderr,
            )
        else:
            print("Frontend ready: http://127.0.0.1:5173/")

    print("Challenge runtime running. Ctrl+C to stop.")
    try:
        while True:
            for proc in procs:
                code = proc.poll()
                if code is not None:
                    print(f"Process exited with {code}", file=sys.stderr)
                    _shutdown()
                    return code or 1
            time.sleep(0.5)
    except KeyboardInterrupt:
        _shutdown()
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
