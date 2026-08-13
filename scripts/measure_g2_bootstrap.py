#!/usr/bin/env python3
"""Measure G2 clean bootstrap wall-clock into docs/G2_BOOTSTRAP.generated.md.

Creates an isolated git worktree (no .venv / node_modules / runtime) and times
the documented challenge bootstrap path. Does not invent timings.

SYSTEM PREREQUISITES (timer does NOT include installing these):
  - Python 3.11+
  - Node.js 20+ / npm
  - GNU Make, Git
  - Ollama installed + daemon reachable + ``ollama pull phi3.5`` already done
  - NVIDIA driver + CUDA-capable GPU (challenge STT cuda)
  - Optional: warm Hugging Face cache for Whisper/Piper (first download is host setup)

PROJECT BOOTSTRAP (timed — matches README ``make lift``):
  cp .env.example .env
  make bootstrap
  make prepare-voice SKIP_FIXTURES=1
  make prepare-llm-bench
  make run-challenge (health probe; preflight runs once inside this command)

Usage:
  python scripts/measure_g2_bootstrap.py
  python scripts/measure_g2_bootstrap.py --skip-run   # stop after preflight
  python scripts/measure_g2_bootstrap.py --strict-clone  # git worktree + isolated pip/npm/HF
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _port_in_use(port: int) -> bool:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.4)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def _run(
    cmd: list[str] | str,
    *,
    cwd: Path,
    env: dict[str, str],
    timeout: int | None = None,
) -> dict[str, Any]:
    shell = isinstance(cmd, str)
    t0 = time.perf_counter()
    try:
        completed = subprocess.run(
            cmd,
            cwd=str(cwd),
            env=env,
            shell=shell,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        elapsed = time.perf_counter() - t0
        return {
            "cmd": cmd if isinstance(cmd, str) else " ".join(cmd),
            "exit_code": completed.returncode,
            "elapsed_s": round(elapsed, 2),
            "stdout_tail": (completed.stdout or "")[-4000:],
            "stderr_tail": (completed.stderr or "")[-2000:],
            "ok": completed.returncode == 0,
        }
    except subprocess.TimeoutExpired as exc:
        elapsed = time.perf_counter() - t0
        return {
            "cmd": cmd if isinstance(cmd, str) else " ".join(cmd),
            "exit_code": -1,
            "elapsed_s": round(elapsed, 2),
            "stdout_tail": (exc.stdout or "")[-2000:] if isinstance(exc.stdout, str) else "",
            "stderr_tail": f"TimeoutExpired:{timeout}",
            "ok": False,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--worktree",
        type=Path,
        default=None,
        help="Worktree path (default: ../limen-g2-bootstrap-<stamp>)",
    )
    parser.add_argument(
        "--skip-run",
        action="store_true",
        help="Do not start run-challenge; stop after prepare-llm-bench",
    )
    parser.add_argument(
        "--keep-worktree",
        action="store_true",
        help="Do not remove the worktree at the end",
    )
    parser.add_argument(
        "--from-head",
        action="store_true",
        help="Use git worktree from HEAD instead of syncing the working tree",
    )
    parser.add_argument(
        "--dataset-path",
        default=os.environ.get("LIMEN_DATASET_PATH", ""),
        help="Optional LIMEN_DATASET_PATH for the clean tree",
    )
    parser.add_argument(
        "--strict-clone",
        action="store_true",
        help=(
            "Measure a git worktree from HEAD with pip/npm/HF caches isolated "
            "inside the worktree. Ollama phi3.5 and system Python/Node stay host prereqs."
        ),
    )
    args = parser.parse_args()
    if args.strict_clone:
        args.from_head = True

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    worktree = args.worktree or (ROOT.parent / f"limen-g2-bootstrap-{stamp}")

    if _port_in_use(8000) or _port_in_use(5173):
        print(
            "Ports 8000/5173 are in use. Stop the running challenge stack "
            "before measuring G2 (otherwise health is not a cold start).",
            file=sys.stderr,
        )
        return 1

    if worktree.exists():
        print(f"Worktree path exists: {worktree}", file=sys.stderr)
        return 1

    stages: list[dict[str, Any]] = []
    env = os.environ.copy()
    # Isolate from developer contamination.
    for key in list(env):
        if (
            key.startswith("LIMEN_")
            and key
            not in {
                "LIMEN_DATASET_PATH",
                "LIMEN_DEMO_EMAIL",
                "LIMEN_DEMO_PASSWORD",
                "LIMEN_DEMO_NAME",
            }
            and key == "LIMEN_RUNTIME_PROFILE"
        ):
            env.pop(key, None)
    if args.dataset_path:
        env["LIMEN_DATASET_PATH"] = args.dataset_path
    env["LIMEN_RUNTIME_PROFILE"] = "challenge"
    cache_root = worktree / ".cache"
    env["TMPDIR"] = str(worktree / ".tmp")
    env["HF_HOME"] = str(cache_root / "huggingface")
    if args.strict_clone:
        env["HUGGINGFACE_HUB_CACHE"] = str(cache_root / "huggingface" / "hub")
        env["HF_HUB_CACHE"] = str(cache_root / "huggingface" / "hub")
        env["TRANSFORMERS_CACHE"] = str(cache_root / "huggingface" / "transformers")
        env["PIP_CACHE_DIR"] = str(cache_root / "pip")
        env["UV_CACHE_DIR"] = str(cache_root / "uv")
        env["NPM_CONFIG_CACHE"] = str(cache_root / "npm")
        env["npm_config_cache"] = str(cache_root / "npm")
        env["XDG_CACHE_HOME"] = str(cache_root)

    report: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "machine": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "node": shutil.which("node"),
            "npm": shutil.which("npm"),
            "ollama": shutil.which("ollama"),
            "hostname": platform.node(),
        },
        "system_prerequisites": [
            "Python 3.11+",
            "Node.js 20+ / npm",
            "Ollama installed and running (phi3.5)",
            "NVIDIA driver + CUDA GPU for STT_DEVICE=cuda",
            "Network for pip/npm/HF/Ollama when assets uncached",
        ],
        "start_conditions": {
            "fresh_worktree": True,
            "no_venv": True,
            "no_node_modules": True,
            "no_runtime_db": True,
            "source_ref": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
            ).strip(),
            "strict_clone": bool(args.strict_clone),
            "isolated_caches": (
                ["pip", "npm", "huggingface", "xdg"] if args.strict_clone else []
            ),
            "host_prereqs_not_timed": [
                "python3",
                "node/npm",
                "ollama + phi3.5 already pulled",
                "nvidia driver + CUDA GPU",
            ],
            "note": (
                "Strict clone: git worktree from HEAD; pip/npm/HF caches empty in the worktree. "
                "Ollama weights and system interpreters are host prerequisites (not timed)."
                if args.strict_clone
                else (
                    "Host package caches (pip/npm/ollama/HF) may still be warm. "
                    "Documented as cached vs cold per stage when detectable."
                )
            ),
        },
        "stages": stages,
        "worktree": str(worktree),
    }

    t_all = time.perf_counter()

    # Prefer measuring the current working tree (includes uncommitted challenge
    # Makefile/scripts the evaluator will receive after the human commits).
    # Fallback: detached git worktree from HEAD when --from-head is set.
    if args.from_head:
        stage = _run(
            ["git", "worktree", "add", "--detach", str(worktree), "HEAD"],
            cwd=ROOT,
            env=env,
        )
        stage["name"] = "git_worktree"
        stages.append(stage)
        if not stage["ok"]:
            _write_report(report, total_s=time.perf_counter() - t_all, success=False)
            return 1
    else:
        t0 = time.perf_counter()
        worktree.mkdir(parents=True, exist_ok=False)
        rsync = [
            "rsync",
            "-a",
            "--delete",
            "--exclude",
            ".venv/",
            "--exclude",
            "apps/web/node_modules/",
            "--exclude",
            "runtime/",
            "--exclude",
            ".tmp/",
            "--exclude",
            ".cache/",
            "--exclude",
            ".git/",
            str(ROOT) + "/",
            str(worktree) + "/",
        ]
        stage = _run(rsync, cwd=ROOT, env=env)
        stage["name"] = "sync_working_tree"
        stage["elapsed_s"] = round(time.perf_counter() - t0, 2)
        stages.append(stage)
        report["start_conditions"]["source"] = "working_tree_rsync"
        report["start_conditions"]["note"] = (
            "Measured from current working tree (excludes .venv/node_modules/runtime). "
            "Host pip/npm/ollama/HF caches may still be warm. "
            "Official jury clone requires these files to be committed."
        )
        if not stage["ok"]:
            _write_report(report, total_s=time.perf_counter() - t_all, success=False)
            return 1

    # Ensure TMPDIR / isolated caches exist inside clean tree.
    (worktree / ".tmp").mkdir(parents=True, exist_ok=True)
    (worktree / ".cache" / "pip").mkdir(parents=True, exist_ok=True)
    (worktree / ".cache" / "npm").mkdir(parents=True, exist_ok=True)
    (worktree / ".cache" / "huggingface").mkdir(parents=True, exist_ok=True)
    env["TMPDIR"] = str(worktree / ".tmp")
    env["HF_HOME"] = str(worktree / ".cache" / "huggingface")

    # Ensure no leftover runtime (worktree is clean by definition).
    assert not (worktree / ".venv").exists()
    assert not (worktree / "apps" / "web" / "node_modules").exists()

    stage = _run(
        "cp .env.example .env",
        cwd=worktree,
        env=env,
    )
    stage["name"] = "copy_env"
    stages.append(stage)

    # Bootstrap: python deps + embeddings + npm
    stage = _run(
        ["make", "bootstrap"],
        cwd=worktree,
        env=env,
        timeout=900,
    )
    stage["name"] = "make_bootstrap"
    stages.append(stage)
    if not stage["ok"]:
        _write_report(report, total_s=time.perf_counter() - t_all, success=False)
        _cleanup(worktree, keep=args.keep_worktree, from_head=args.from_head)
        return 1

    stage = _run(
        ["make", "prepare-voice", "SKIP_FIXTURES=1"],
        cwd=worktree,
        env=env,
        timeout=1200,
    )
    stage["name"] = "make_prepare_voice"
    stages.append(stage)

    stage = _run(
        ["make", "prepare-llm-bench"],
        cwd=worktree,
        env=env,
        timeout=120,
    )
    stage["name"] = "make_prepare_llm"
    stages.append(stage)

    health: dict[str, Any] | None = None
    urls = {
        "api_health": "http://127.0.0.1:8000/health",
        "web": "http://127.0.0.1:5173",
        "openapi": "http://127.0.0.1:8000/docs",
    }
    report["urls"] = urls
    ready = False

    if not args.skip_run:
        # Start challenge stack briefly and probe health.
        # Preflight runs once inside run-challenge (do not verify twice).
        log_path = worktree / "runtime" / "logs" / "g2_run_challenge.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        t0 = time.perf_counter()
        proc = subprocess.Popen(
            ["make", "run-challenge"],
            cwd=str(worktree),
            env=env,
            stdout=log_path.open("w"),
            stderr=subprocess.STDOUT,
        )
        health_ok = False
        deadline = time.time() + 180
        while time.time() < deadline:
            try:
                import urllib.request

                with urllib.request.urlopen(urls["api_health"], timeout=2) as resp:
                    body = resp.read().decode("utf-8")
                    health = json.loads(body)
                    if resp.status == 200:
                        health_ok = True
                        ready = True
                        break
            except Exception:  # noqa: BLE001
                time.sleep(2)
        elapsed = time.perf_counter() - t0
        stages.append(
            {
                "name": "run_challenge_health",
                "elapsed_s": round(elapsed, 2),
                "ok": health_ok,
                "cmd": "make run-challenge",
                "exit_code": None,
            }
        )
        report["health"] = health
        report["READY_FOR_CHALLENGE_RUNTIME"] = ready
        proc.terminate()
        try:
            proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()
    else:
        stage = _run(
            ["make", "verify-challenge-environment"],
            cwd=worktree,
            env=env,
            timeout=300,
        )
        stage["name"] = "verify_challenge_environment"
        stages.append(stage)
        ready = "READY_FOR_CHALLENGE_RUNTIME=TRUE" in (
            stage.get("stdout_tail", "") + stage.get("stderr_tail", "")
        )
        report["READY_FOR_CHALLENGE_RUNTIME"] = ready

    total_s = time.perf_counter() - t_all
    success = ready and all(
        s.get("ok", True)
        for s in stages
        if s.get("name")
        in {
            "git_worktree",
            "copy_env",
            "make_bootstrap",
            "make_prepare_voice",
            "make_prepare_llm",
        }
    )

    report["total_min"] = round(total_s / 60.0, 2)
    report["g2_le_15_min"] = total_s <= 15 * 60
    report["success"] = success
    report["g2_status"] = (
        "PASS" if success and report["g2_le_15_min"] and ready else "PARTIAL" if success else "FAIL"
    )

    _write_report(report, total_s=total_s, success=success)
    _cleanup(worktree, keep=args.keep_worktree, from_head=args.from_head)
    print(
        json.dumps(
            {
                k: report[k]
                for k in (
                    "total_s",
                    "total_min",
                    "g2_le_15_min",
                    "READY_FOR_CHALLENGE_RUNTIME",
                    "g2_status",
                    "success",
                )
            },
            indent=2,
        )
    )
    return 0 if success else 1


def _write_report(report: dict[str, Any], *, total_s: float, success: bool) -> None:
    report.setdefault("total_s", round(total_s, 2))
    report.setdefault("success", success)
    out_json = ROOT / "runtime" / "evals" / "g2" / "latest.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    md = ROOT / "docs" / "G2_BOOTSTRAP.generated.md"
    lines = [
        "# G2 Bootstrap Evidence (generated)",
        "",
        f"Generated: {report.get('generated_at')}",
        f"Machine: `{report.get('machine', {}).get('hostname')}` "
        f"({report.get('machine', {}).get('platform')})",
        f"Total: **{report.get('total_s')}s** "
        f"({report.get('total_min', round(total_s / 60, 2))} min)",
        f"≤15 min: **{report.get('g2_le_15_min')}**",
        f"READY_FOR_CHALLENGE_RUNTIME: **{report.get('READY_FOR_CHALLENGE_RUNTIME')}**",
        f"G2 status: **{report.get('g2_status', 'UNVERIFIED')}**",
        "",
        "## System prerequisites (before timer)",
        "",
    ]
    for item in report.get("system_prerequisites", []):
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Start conditions",
            "",
            "```json",
            json.dumps(report.get("start_conditions", {}), indent=2),
            "```",
            "",
            "## Commands / stages",
            "",
        ]
    )
    for stage in report.get("stages", []):
        lines.append(
            f"- `{stage.get('name')}`: {stage.get('elapsed_s')}s "
            f"ok={stage.get('ok')} — `{stage.get('cmd')}`"
        )
    lines.extend(
        [
            "",
            "## URLs",
            "",
            f"- API health: {report.get('urls', {}).get('api_health')}",
            f"- Web: {report.get('urls', {}).get('web')}",
            "",
            "## Health result",
            "",
            "```json",
            json.dumps(report.get("health"), indent=2, ensure_ascii=False)[:4000],
            "```",
            "",
            f"Machine-readable: `{out_json}`",
            "",
        ]
    )
    md.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {md}")


def _cleanup(worktree: Path, *, keep: bool, from_head: bool = False) -> None:
    if keep:
        return
    if from_head:
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(worktree)],
            cwd=str(ROOT),
            check=False,
            capture_output=True,
        )
    else:
        shutil.rmtree(worktree, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
