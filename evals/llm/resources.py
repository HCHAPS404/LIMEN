"""Light resource probes for TEXT LLM inference metrics (no heavy deps)."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def process_rss_bytes(pid: int) -> int | None:
    try:
        status = Path(f"/proc/{pid}/status").read_text(encoding="utf-8")
    except OSError:
        return None
    for line in status.splitlines():
        if line.startswith("VmRSS:"):
            # kB
            parts = line.split()
            if len(parts) >= 2:
                return int(parts[1]) * 1024
    return None


def find_ollama_server_rss_bytes() -> int | None:
    """Best-effort RSS of an ollama serve / ollama runner process."""
    proc = Path("/proc")
    if not proc.is_dir():
        return None
    best: int | None = None
    try:
        for entry in proc.iterdir():
            if not entry.name.isdigit():
                continue
            try:
                cmdline = (entry / "cmdline").read_bytes().decode("utf-8", errors="ignore")
            except OSError:
                continue
            lower = cmdline.lower().replace("\x00", " ")
            if "ollama" not in lower:
                continue
            if "serve" in lower or "runner" in lower or lower.strip().endswith("ollama"):
                rss = process_rss_bytes(int(entry.name))
                if rss is not None and (best is None or rss > best):
                    best = rss
    except OSError:
        return None
    return best


def snapshot_resources() -> dict[str, Any]:
    return {
        "ollama_rss_bytes": find_ollama_server_rss_bytes(),
        "note": (
            "RSS from /proc when available; UNMEASURED/null if not measurable. "
            "Never estimated from model file size."
        ),
    }
