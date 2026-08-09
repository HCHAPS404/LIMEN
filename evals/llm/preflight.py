"""Deterministic Ollama / G3 LLM benchmark preflight (no sudo, no auto-pull)."""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from limen.intelligence.providers.ollama import is_g3_allowed_ollama_model

ROOT = Path(__file__).resolve().parents[2]

# Exact local G3 runtime candidates for PHASE 5/5B.
G3_LOCAL_CANDIDATES: tuple[str, ...] = ("llama3.2:1b", "llama3.2:3b", "phi3.5")

# Acceptable installed tags that map to the same candidate id.
CANDIDATE_TAG_ALIASES: dict[str, tuple[str, ...]] = {
    "llama3.2:1b": ("llama3.2:1b",),
    "llama3.2:3b": ("llama3.2:3b",),
    "phi3.5": ("phi3.5", "phi3.5:latest", "phi3.5:3.8b"),
}


@dataclass
class CandidateStatus:
    candidate_id: str
    installed: bool
    resolved_tag: str | None = None
    digest: str | None = None
    quantization: str | None = None
    parameter_size: str | None = None
    family: str | None = None
    size_bytes: int | None = None
    runnable: bool = False
    notes: str = ""


@dataclass
class PreflightReport:
    generated_at: str
    ollama_binary: str | None
    binary_ok: bool
    server_ok: bool
    base_url: str
    ollama_version: str | None
    installed_models: list[str] = field(default_factory=list)
    candidates: list[CandidateStatus] = field(default_factory=list)
    runtime_dirs_writable: dict[str, bool] = field(default_factory=dict)
    hardware: dict[str, Any] = field(default_factory=dict)
    operator_instructions: list[str] = field(default_factory=list)
    ready_for_benchmark: bool = False
    blocking_reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        return data


def default_base_url() -> str:
    return (os.environ.get("LLM_BASE_URL") or "http://127.0.0.1:11434").rstrip("/")


def detect_nvidia_gpu() -> dict[str, Any]:
    """Return GPU name and VRAM bytes from nvidia-smi, or UNMEASURED fields."""
    try:
        out = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total",
                "--format=csv,noheader,nounits",
            ],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=3,
        ).strip()
        if not out:
            return {"name": "UNMEASURED", "vram_bytes": "UNMEASURED"}
        line = out.splitlines()[0]
        parts = [part.strip() for part in line.split(",")]
        name = parts[0] if parts else "UNMEASURED"
        vram_bytes: int | str = "UNMEASURED"
        if len(parts) > 1:
            try:
                vram_bytes = int(float(parts[1]) * 1024 * 1024)
            except ValueError:
                vram_bytes = "UNMEASURED"
        return {"name": name, "vram_bytes": vram_bytes}
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return {"name": "UNMEASURED", "vram_bytes": "UNMEASURED"}


def detect_nvidia_gpu() -> dict[str, Any]:
    """Return GPU name and VRAM bytes from nvidia-smi, or UNMEASURED fields."""
    try:
        out = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total",
                "--format=csv,noheader,nounits",
            ],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=3,
        ).strip()
        if not out:
            return {"name": "UNMEASURED", "vram_bytes": "UNMEASURED"}
        line = out.splitlines()[0]
        parts = [part.strip() for part in line.split(",")]
        name = parts[0] if parts else "UNMEASURED"
        vram_bytes: int | str = "UNMEASURED"
        if len(parts) > 1:
            try:
                vram_bytes = int(float(parts[1]) * 1024 * 1024)
            except ValueError:
                vram_bytes = "UNMEASURED"
        return {"name": name, "vram_bytes": vram_bytes}
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return {"name": "UNMEASURED", "vram_bytes": "UNMEASURED"}


def collect_hardware() -> dict[str, Any]:
    ram_bytes: int | None = None
    try:
        # Linux MemTotal in kB
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            if line.startswith("MemTotal:"):
                ram_bytes = int(line.split()[1]) * 1024
                break
    except OSError:
        ram_bytes = None

    cpu_model = platform.processor() or None
    try:
        cpuinfo = Path("/proc/cpuinfo").read_text(encoding="utf-8")
        for line in cpuinfo.splitlines():
            if line.startswith("model name"):
                cpu_model = line.split(":", 1)[1].strip()
                break
    except OSError:
        pass

    gpu_detail = detect_nvidia_gpu()
    gpu_name = gpu_detail.get("name")
    gpu_display = gpu_name if gpu_name and gpu_name != "UNMEASURED" else "UNMEASURED"

    return {
        "os": platform.platform(),
        "kernel": platform.release(),
        "machine": platform.machine(),
        "cpu": cpu_model,
        "ram_bytes": ram_bytes,
        "gpu": gpu_display,
        "gpu_name": gpu_detail.get("name", "UNMEASURED"),
        "gpu_vram_bytes": gpu_detail.get("vram_bytes", "UNMEASURED"),
        "python": platform.python_version(),
    }


def _writable(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def _resolve_tag(installed: list[str], aliases: tuple[str, ...]) -> str | None:
    installed_l = {m.lower(): m for m in installed}
    for alias in aliases:
        if alias.lower() in installed_l:
            return installed_l[alias.lower()]
        for name, original in installed_l.items():
            if name.startswith(f"{alias.lower()}@"):
                return original
    return None


def _show_model(base_url: str, tag: str) -> dict[str, Any]:
    try:
        response = httpx.post(
            f"{base_url}/api/show",
            json={"name": tag},
            timeout=30.0,
        )
        if response.status_code != 200:
            return {}
        data = response.json()
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def run_preflight(*, base_url: str | None = None, pull_hint: bool = True) -> PreflightReport:
    base = (base_url or default_base_url()).rstrip("/")
    binary = shutil.which("ollama")
    report = PreflightReport(
        generated_at=datetime.now(tz=UTC).isoformat(),
        ollama_binary=binary,
        binary_ok=bool(binary),
        server_ok=False,
        base_url=base,
        ollama_version=None,
        hardware=collect_hardware(),
    )

    runtime_root = ROOT / "runtime" / "benchmarks" / "llm"
    report.runtime_dirs_writable = {
        "runtime/benchmarks/llm": _writable(runtime_root),
        "runtime/benchmarks/llm/runs": _writable(runtime_root / "runs"),
        "docs": _writable(ROOT / "docs"),
    }
    for name, ok in report.runtime_dirs_writable.items():
        if not ok:
            report.blocking_reasons.append(f"not_writable:{name}")

    if not binary:
        report.blocking_reasons.append("ollama_binary_missing")
        report.operator_instructions.extend(
            [
                "Ollama binary not found on PATH.",
                "On Arch Linux (operator must run; scripts never use sudo):",
                "  sudo pacman -S ollama",
                "  sudo systemctl enable --now ollama.service",
                "Then verify: ollama --version && curl -sS http://127.0.0.1:11434/api/version",
            ]
        )

    # Server health even if binary missing (remote URL possible).
    try:
        version_resp = httpx.get(f"{base}/api/version", timeout=3.0)
        tags_resp = httpx.get(f"{base}/api/tags", timeout=5.0)
        if version_resp.status_code == 200 and tags_resp.status_code == 200:
            report.server_ok = True
            ver = version_resp.json()
            report.ollama_version = (
                str(ver.get("version")) if isinstance(ver, dict) else version_resp.text
            )
            tags = tags_resp.json()
            models = []
            if isinstance(tags, dict):
                for item in tags.get("models") or []:
                    name = str(item.get("name") or "")
                    if name:
                        models.append(name)
            report.installed_models = models
        else:
            report.blocking_reasons.append(
                f"ollama_http_status:version={version_resp.status_code},tags={tags_resp.status_code}"
            )
    except Exception as exc:
        report.blocking_reasons.append(f"ollama_unreachable:{type(exc).__name__}:{exc}")
        if binary:
            report.operator_instructions.extend(
                [
                    f"Ollama binary found at {binary} but server not reachable at {base}.",
                    "Start the service (operator):",
                    "  sudo systemctl enable --now ollama.service",
                    "  # or: ollama serve",
                ]
            )

    missing: list[str] = []
    for candidate_id in G3_LOCAL_CANDIDATES:
        aliases = CANDIDATE_TAG_ALIASES[candidate_id]
        resolved = _resolve_tag(report.installed_models, aliases)
        status = CandidateStatus(
            candidate_id=candidate_id,
            installed=resolved is not None,
            resolved_tag=resolved,
        )
        if resolved and report.server_ok:
            shown = _show_model(base, resolved)
            details = shown.get("details") if isinstance(shown.get("details"), dict) else {}
            status.digest = (
                str(shown.get("modelfile"))[:64] + "…"
                if isinstance(shown.get("modelfile"), str) and shown.get("modelfile")
                else None
            )
            # Prefer model digest fields when present.
            for key in ("digest", "model_digest", "sha256"):
                if shown.get(key):
                    status.digest = str(shown[key])
                    break
            model_info = shown.get("model_info")
            if isinstance(model_info, dict):
                for key, value in model_info.items():
                    if "digest" in str(key).lower() and value:
                        status.digest = str(value)
                        break
            status.quantization = (
                str(details.get("quantization_level"))
                if details.get("quantization_level") is not None
                else None
            )
            status.parameter_size = (
                str(details.get("parameter_size"))
                if details.get("parameter_size") is not None
                else None
            )
            status.family = (
                str(details.get("family")) if details.get("family") is not None else None
            )
            size = shown.get("size")
            status.size_bytes = int(size) if isinstance(size, int) else None
            status.runnable = is_g3_allowed_ollama_model(resolved)
            if not status.runnable:
                status.notes = "resolved_tag_not_g3_allowed"
        else:
            missing.append(candidate_id)
            status.notes = "not_installed"
        report.candidates.append(status)

    if missing and pull_hint:
        report.blocking_reasons.append("missing_g3_candidates:" + ",".join(missing))
        report.operator_instructions.append("Pull missing G3 candidates explicitly:")
        for mid in missing:
            report.operator_instructions.append(f"  ollama pull {mid}")
        report.operator_instructions.append("Or: make prepare-llm-bench PULL=1")

    # Disallow non-G3 installed models from being treated as candidates.
    for installed in report.installed_models:
        if installed.split(":")[0].startswith(("llama3.3", "llama4", "phi4", "qwen", "mistral")):
            # informational only
            pass

    runnable = [c for c in report.candidates if c.runnable]
    report.ready_for_benchmark = (
        report.server_ok
        and bool(runnable)
        and all(report.runtime_dirs_writable.values())
        and not any(r.startswith("ollama_") for r in report.blocking_reasons if "missing" not in r)
    )
    # Ready if at least one candidate runnable and server ok; missing others are warnings.
    if report.server_ok and runnable and all(report.runtime_dirs_writable.values()):
        report.ready_for_benchmark = True
        # Keep missing as blocking only when ZERO candidates runnable.
        report.blocking_reasons = [
            r for r in report.blocking_reasons if not r.startswith("missing_g3_candidates")
        ]
        if len(runnable) < len(G3_LOCAL_CANDIDATES):
            report.operator_instructions.append(
                "Note: benchmark can run with a subset; missing models remain UNAVAILABLE."
            )
    elif report.server_ok and not runnable:
        report.ready_for_benchmark = False

    return report


def print_preflight(report: PreflightReport) -> int:
    print("LIMEN LLM benchmark preflight")
    print(f"  binary: {report.ollama_binary or 'MISSING'}")
    print(f"  server_ok: {report.server_ok}")
    print(f"  base_url: {report.base_url}")
    print(f"  version: {report.ollama_version or 'UNMEASURED'}")
    print(f"  ready_for_benchmark: {report.ready_for_benchmark}")
    for cand in report.candidates:
        print(
            f"  candidate {cand.candidate_id}: installed={cand.installed} "
            f"resolved={cand.resolved_tag} runnable={cand.runnable} "
            f"quant={cand.quantization or 'UNMEASURED'} "
            f"size={cand.size_bytes if cand.size_bytes is not None else 'UNMEASURED'}"
        )
    if report.blocking_reasons:
        print("  blocking:")
        for reason in report.blocking_reasons:
            print(f"    - {reason}")
    if report.operator_instructions:
        print("  operator instructions:")
        for line in report.operator_instructions:
            print(f"    {line}")
    return 0 if report.ready_for_benchmark else 2


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = run_preflight(base_url=args.base_url)
    if args.json:
        print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
        return 0 if report.ready_for_benchmark else 2
    return print_preflight(report)


if __name__ == "__main__":
    raise SystemExit(main())
