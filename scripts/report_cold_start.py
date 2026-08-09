#!/usr/bin/env python3
"""Report evaluator-relevant cold-start phases (measured or UNMEASURED).

Does not download models unless --load-model is passed.
Does not invent timings — missing measurements are marked UNMEASURED.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from limen.config.settings import get_settings
from limen.knowledge.embeddings import (
    local_model_available,
    resolve_embedding_model_name,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--load-model",
        action="store_true",
        help="Time model initialization (loads weights; may download if uncached)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON",
    )
    args = parser.parse_args()

    settings = get_settings()
    report: dict[str, object] = {
        "dependency_install": "UNMEASURED",
        "model_acquisition": "UNMEASURED",
        "model_initialization": "UNMEASURED",
        "application_start": "UNMEASURED",
        "ready_check": "UNMEASURED",
        "notes": [
            "Dependency install is measured by the operator during `make bootstrap`.",
            "Model acquisition is UNMEASURED unless Hub/local fetch is timed separately.",
            "Do not equate model initialization with full cold-start.",
            "The ≤15 minute claim requires a real end-to-end cold-start run.",
        ],
    }

    model_ref = resolve_embedding_model_name(settings)
    local = local_model_available(settings)
    report["resolved_model"] = model_ref
    report["local_model_available"] = local
    if local:
        report["model_acquisition"] = "CACHED (local path or prior download)"
    else:
        report["model_acquisition"] = "UNMEASURED (would use Hugging Face Hub on first real load)"

    if args.load_model:
        if settings.embedding_provider.lower().strip() == "stub":
            report["model_initialization"] = "N/A (stub provider)"
        else:
            from limen.knowledge.embeddings import build_embedding_provider

            t0 = time.perf_counter()
            provider = build_embedding_provider(settings)
            _ = provider.embed_query("cold start probe")
            elapsed = time.perf_counter() - t0
            report["model_initialization"] = f"{elapsed:.2f}s"
            report["embedding_dimensions"] = provider.dimensions

    # Lightweight ready check without loading embeddings unless already loaded.
    t0 = time.perf_counter()
    settings.ensure_runtime_dirs()
    vector_ok = settings.vector_path.exists() and settings.vector_path.is_dir()
    ready_elapsed = time.perf_counter() - t0
    report["ready_check"] = f"{ready_elapsed:.3f}s (runtime dirs)"
    report["vector_path_writable"] = _writable(settings.vector_path)

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print("LIMEN cold-start phases")
        for key in (
            "dependency_install",
            "model_acquisition",
            "model_initialization",
            "application_start",
            "ready_check",
        ):
            print(f"  {key}: {report[key]}")
        print(f"  resolved_model: {report['resolved_model']}")
        print(f"  local_model_available: {report['local_model_available']}")
        print(f"  vector_path_writable: {report['vector_path_writable']}")
        for note in report["notes"]:  # type: ignore[union-attr]
            print(f"  note: {note}")
    return 0 if vector_ok else 1


def _writable(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except OSError:
        return False


if __name__ == "__main__":
    raise SystemExit(main())
