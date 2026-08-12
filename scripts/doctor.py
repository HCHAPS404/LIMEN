#!/usr/bin/env python3
"""Cross-platform readiness report for LIMEN (stubs + challenge hints).

Safe to run before or after ``make bootstrap``. Does not download models.
Ends with machine-readable lines:

  READY_STUBS=TRUE|FALSE
  READY_CHALLENGE_HINT=TRUE|FALSE|UNKNOWN
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass
class Check:
    name: str
    ok: bool
    detail: str
    level: str = "host"  # host | stubs | challenge


def _run(cmd: list[str], timeout: float = 8.0) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        out = (proc.stdout or proc.stderr or "").strip()
        return proc.returncode, out
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, f"{type(exc).__name__}: {exc}"


def _detect_os() -> Check:
    system = platform.system()
    release = platform.release()
    machine = platform.machine()
    wsl = False
    if system == "Linux":
        try:
            wsl = "microsoft" in Path("/proc/version").read_text(encoding="utf-8").lower()
        except OSError:
            wsl = "WSL_DISTRO_NAME" in os.environ or "WSL_INTEROP" in os.environ
    if system == "Windows" and not wsl:
        detail = (
            f"{system} {release} ({machine}) — use WSL2 (Ubuntu) for the supported path; "
            "native PowerShell is best-effort"
        )
        return Check("os", True, detail, "host")
    if wsl:
        return Check("os", True, f"WSL2/Linux {release} ({machine})", "host")
    if system in {"Linux", "Darwin"}:
        return Check("os", True, f"{system} {release} ({machine})", "host")
    return Check("os", False, f"unsupported platform: {system} {release}", "host")


def _venv_python() -> Path | None:
    unix = ROOT / ".venv" / "bin" / "python"
    win = ROOT / ".venv" / "Scripts" / "python.exe"
    if unix.is_file():
        return unix
    if win.is_file():
        return win
    return None


def _check_python() -> Check:
    ver = sys.version_info
    ok = ver >= (3, 11)
    return Check(
        "python",
        ok,
        f"{platform.python_version()} ({sys.executable})"
        + ("" if ok else " — need Python 3.11+"),
        "host",
    )


def _check_cmd(name: str, args: list[str], min_major: int | None = None) -> Check:
    exe = shutil.which(args[0])
    if not exe:
        return Check(name, False, f"{args[0]} not found on PATH", "host")
    code, out = _run(args)
    if code != 0 and not out:
        return Check(name, False, f"{args[0]} present but probe failed", "host")
    first = (out.splitlines() or [""])[0].strip()
    if min_major is not None:
        # node -v → v20.x.x
        digits = "".join(ch if ch.isdigit() or ch == "." else " " for ch in first)
        major_s = digits.strip().split(".", maxsplit=1)[0]
        try:
            major = int(major_s)
        except ValueError:
            major = -1
        if major < min_major:
            return Check(
                name,
                False,
                f"{first} — need major >={min_major}",
                "host",
            )
    return Check(name, True, first or exe, "host")


def _check_make() -> Check:
    if shutil.which("make"):
        code, out = _run(["make", "--version"])
        first = (out.splitlines() or ["make"])[0]
        return Check("make", code == 0 or "Make" in out or "make" in out.lower(), first, "host")
    system = platform.system()
    hint = {
        "Windows": "install Git Bash + make, or use WSL2",
        "Darwin": "xcode-select --install or brew install make",
        "Linux": "sudo apt/dnf/pacman install make",
    }.get(system, "install GNU make")
    return Check("make", False, f"make not on PATH ({hint})", "host")


def _check_env_file() -> Check:
    env_path = ROOT / ".env"
    example = ROOT / ".env.example"
    if env_path.is_file():
        return Check(".env", True, str(env_path.relative_to(ROOT)), "stubs")
    if example.is_file():
        return Check(
            ".env",
            False,
            "missing — copy .env.example to .env (Windows cmd: copy .env.example .env)",
            "stubs",
        )
    return Check(".env", False, "missing .env and .env.example", "stubs")


def _check_venv() -> Check:
    py = _venv_python()
    if py is None:
        return Check(
            ".venv",
            False,
            "missing — run: make bootstrap",
            "stubs",
        )
    code, out = _run([str(py), "--version"])
    ok = code == 0
    return Check(".venv", ok, f"{py.relative_to(ROOT)} → {out or 'ok'}", "stubs")


def _check_node_modules() -> Check:
    pkg = ROOT / "apps" / "web" / "node_modules"
    if pkg.is_dir():
        return Check("web/node_modules", True, "present", "stubs")
    return Check(
        "web/node_modules",
        False,
        "missing — run make bootstrap (installs apps/web deps)",
        "stubs",
    )


def _check_runtime_dirs() -> Check:
    runtime = ROOT / "runtime"
    if runtime.is_dir():
        return Check("runtime/", True, "present (gitignored; created locally)", "stubs")
    return Check(
        "runtime/",
        False,
        "absent until bootstrap/run — will be created",
        "stubs",
    )


def _check_providers_via_settings() -> list[Check]:
    checks: list[Check] = []
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    try:
        from limen.config.settings import get_settings

        settings = get_settings()
    except Exception as exc:  # noqa: BLE001 — doctor must never crash on import
        checks.append(
            Check(
                "settings",
                False,
                f"cannot load settings ({type(exc).__name__}: {exc})",
                "stubs",
            )
        )
        return checks

    stubs = all(
        getattr(settings, name).lower().strip() == "stub"
        for name in ("llm_provider", "stt_provider", "tts_provider", "embedding_provider")
    )
    profile = getattr(settings, "runtime_profile", "development")
    checks.append(
        Check(
            "providers",
            True,
            (
                f"profile={profile} "
                f"llm={settings.llm_provider} stt={settings.stt_provider} "
                f"tts={settings.tts_provider} emb={settings.embedding_provider}"
                + (" (stubs OK for Nivel 1)" if stubs else " (non-stub — challenge/custom)")
            ),
            "stubs",
        )
    )
    demo = bool(getattr(settings, "has_demo_account", lambda: False)())
    checks.append(
        Check(
            "demo_account_config",
            demo,
            "LIMEN_DEMO_EMAIL/PASSWORD set" if demo else "demo account env empty",
            "stubs",
        )
    )
    return checks


def _check_ollama() -> Check:
    if not shutil.which("ollama"):
        return Check(
            "ollama",
            False,
            "not on PATH — required only for Nivel 3 (challenge)",
            "challenge",
        )
    code, out = _run(["ollama", "list"], timeout=12.0)
    has_phi = "phi3.5" in out.replace(" ", "").lower() or "phi3.5" in out
    if code != 0:
        return Check(
            "ollama",
            False,
            "installed but not responding — start: ollama serve",
            "challenge",
        )
    return Check(
        "ollama",
        True,
        "reachable" + ("; phi3.5 listed" if has_phi else "; pull phi3.5 for challenge"),
        "challenge",
    )


def _check_nvidia() -> Check:
    if not shutil.which("nvidia-smi"):
        return Check(
            "nvidia-smi",
            False,
            "absent — Nivel 3 STT may use CPU fallback if allowed; CUDA recommended on Linux/WSL",
            "challenge",
        )
    code, out = _run(
        ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
        timeout=10.0,
    )
    if code != 0:
        return Check("nvidia-smi", False, out or "probe failed", "challenge")
    gpu = (out.splitlines() or ["GPU"])[0].strip()
    return Check("nvidia-smi", True, gpu, "challenge")


def _check_dataset() -> Check:
    env = os.environ.get("LIMEN_DATASET_PATH", "").strip()
    candidates = []
    if env:
        candidates.append(Path(env))
    candidates.extend([ROOT / "dataset", ROOT / "data" / "challenge"])
    for path in candidates:
        if path.is_dir():
            return Check(
                "official_dataset",
                True,
                f"found at {path} (optional for Nivel 1 / G5 live upload)",
                "challenge",
            )
    return Check(
        "official_dataset",
        False,
        "not mounted — optional; set LIMEN_DATASET_PATH for official PDFs",
        "challenge",
    )


def _check_voice_assets() -> Check:
    piper = ROOT / "runtime" / "models" / "piper"
    if piper.is_dir() and any(piper.iterdir()):
        return Check("voice_assets", True, f"{piper.relative_to(ROOT)} present", "challenge")
    return Check(
        "voice_assets",
        False,
        "missing — Nivel 3: make prepare-voice",
        "challenge",
    )


def main() -> int:
    checks: list[Check] = [
        _detect_os(),
        _check_python(),
        _check_cmd("node", ["node", "--version"], min_major=20),
        _check_cmd("npm", ["npm", "--version"]),
        _check_make(),
        _check_env_file(),
        _check_venv(),
        _check_node_modules(),
        _check_runtime_dirs(),
    ]
    checks.extend(_check_providers_via_settings())
    checks.extend(
        [
            _check_ollama(),
            _check_nvidia(),
            _check_voice_assets(),
            _check_dataset(),
        ]
    )

    print("LIMEN doctor — host / stubs / challenge hints")
    print(f"root: {ROOT}")
    print("")
    for c in checks:
        mark = "OK" if c.ok else "MISSING"
        # runtime/ absent is informational for stubs
        if c.name == "runtime/" and not c.ok:
            mark = "INFO"
        if c.name in {"ollama", "nvidia-smi", "official_dataset", "voice_assets"} and not c.ok:
            mark = "OPTIONAL" if c.name != "ollama" else "MISSING"
        print(f"  [{mark:8}] ({c.level:9}) {c.name}: {c.detail}")

    host_required = [c for c in checks if c.level == "host" and c.name != "os"]
    stubs_files = [c for c in checks if c.name in {".env", ".venv", "web/node_modules"}]
    settings_block = any(not c.ok for c in checks if c.name == "settings")

    ready_stubs = (
        all(c.ok for c in host_required)
        and all(c.ok for c in stubs_files)
        and not settings_block
    )
    # Challenge hint: ollama reachable is the main gate; GPU/dataset optional
    ollama = next(c for c in checks if c.name == "ollama")
    ready_challenge = ready_stubs and ollama.ok

    print("")
    print(f"READY_STUBS={'TRUE' if ready_stubs else 'FALSE'}")
    print(f"READY_CHALLENGE_HINT={'TRUE' if ready_challenge else 'FALSE'}")
    print("")
    if not ready_stubs:
        print("Next (Nivel 1):")
        print("  1. Ensure Python 3.11+, Node 20+, GNU make")
        print("  2. cp .env.example .env   (Windows cmd: copy .env.example .env)")
        print("  3. make bootstrap")
        print("  4. make run   +   make dev-web")
        print("  5. make smoke-local")
    else:
        print("Nivel 1 stubs: host looks ready. Start API+web, then: make smoke-local")
    if not ready_challenge:
        print(
            "Nivel 3 challenge still needs: "
            "Ollama + prepare-voice + verify-challenge-environment"
        )
    print("Docs: README.md · docs/GETTING_STARTED.md · docs/CHALLENGE_RUNTIME.md")
    return 0 if ready_stubs else 1


if __name__ == "__main__":
    raise SystemExit(main())
