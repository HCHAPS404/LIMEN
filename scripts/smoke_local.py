#!/usr/bin/env python3
"""Smoke-check a locally running LIMEN API (and optional web UI).

Expects ``make run`` (or challenge API) already listening.
Does not start servers. Cross-platform (stdlib urllib only).

  SMOKE_API=PASS|FAIL
  SMOKE_WEB=PASS|FAIL|SKIP
  SMOKE_LOCAL=PASS|FAIL
"""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from typing import Any


def _get_json(url: str, timeout: float) -> tuple[int, Any]:
    req = urllib.request.Request(url, method="GET", headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            status = getattr(resp, "status", 200)
            try:
                return int(status), json.loads(body) if body else {}
            except json.JSONDecodeError:
                return int(status), {"_raw": body[:200]}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
        try:
            payload: Any = json.loads(body) if body else {}
        except json.JSONDecodeError:
            payload = {"_raw": body[:200]}
        return int(exc.code), payload
    except urllib.error.URLError as exc:
        raise ConnectionError(str(exc.reason if hasattr(exc, "reason") else exc)) from exc


def _get_ok(url: str, timeout: float) -> tuple[int, str]:
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return int(getattr(resp, "status", 200)), "ok"
    except urllib.error.HTTPError as exc:
        return int(exc.code), str(exc.reason)
    except urllib.error.URLError as exc:
        raise ConnectionError(str(exc.reason if hasattr(exc, "reason") else exc)) from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--api",
        default="http://127.0.0.1:8000",
        help="API base URL (default http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--web",
        default="http://127.0.0.1:5173",
        help="Web base URL (default http://127.0.0.1:5173)",
    )
    parser.add_argument(
        "--skip-web",
        action="store_true",
        help="Only check API /health",
    )
    parser.add_argument("--timeout", type=float, default=3.0)
    args = parser.parse_args()

    api_base = args.api.rstrip("/")
    web_base = args.web.rstrip("/")

    print("LIMEN smoke-local")
    print(f"  API: {api_base}/health")
    if not args.skip_web:
        print(f"  WEB: {web_base}/")
    print("")

    api_pass = False
    try:
        status, payload = _get_json(f"{api_base}/health", args.timeout)
        api_pass = status == 200
        print(f"  API /health → HTTP {status}")
        if isinstance(payload, dict):
            for key in ("status", "runtime_profile", "stub_providers", "database"):
                if key in payload:
                    print(f"    {key}: {payload[key]}")
            if not any(k in payload for k in ("status", "runtime_profile")):
                print(f"    body: {payload}")
    except ConnectionError as exc:
        print(f"  API /health → FAIL ({exc})")
        print("    Hint: start the API in another terminal: make run")
        print("    Then retry: make smoke-local")

    web_status = "SKIP"
    web_pass = True
    if not args.skip_web:
        web_pass = False
        try:
            status, _ = _get_ok(f"{web_base}/", args.timeout)
            web_pass = status == 200
            web_status = "PASS" if web_pass else "FAIL"
            print(f"  WEB / → HTTP {status}")
            if not web_pass:
                print("    Hint: start the UI: make dev-web")
        except ConnectionError as exc:
            web_status = "FAIL"
            print(f"  WEB / → FAIL ({exc})")
            print("    Hint: start the UI: make dev-web")

    print("")
    print(f"SMOKE_API={'PASS' if api_pass else 'FAIL'}")
    print(f"SMOKE_WEB={web_status}")
    overall = api_pass and web_pass
    print(f"SMOKE_LOCAL={'PASS' if overall else 'FAIL'}")
    if overall:
        print("")
        print("Open http://127.0.0.1:5173/  login demo@limen.local / limen-demo-2026")
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
