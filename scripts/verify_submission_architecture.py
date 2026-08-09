#!/usr/bin/env python3
"""Verify submission diagram components exist in the codebase."""

from __future__ import annotations

import importlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CHECKS = [
    ("limen.safety.governor", "SafetyGovernor"),
    ("limen.knowledge.hybrid", "HybridEvidenceRetriever"),
    ("limen.intelligence.providers.ollama", "OllamaLLMProvider"),
    ("limen.voice.providers.faster_whisper_stt", "FasterWhisperSTTProvider"),
    ("limen.voice.providers.piper_tts", "PiperTTSProvider"),
    ("limen.conversation.context", "ConversationContext"),
    ("limen.knowledge.ingestion", "KnowledgeIngestionService"),
    ("limen.knowledge.deletion", "KnowledgeDeletionService"),
    ("limen.tracing.events", "TraceEvent"),
]


def main() -> int:
    results = []
    ok = True
    for module_name, attr in CHECKS:
        try:
            mod = importlib.import_module(module_name)
            present = hasattr(mod, attr)
            if not present:
                ok = False
            results.append({"module": module_name, "attr": attr, "ok": present})
        except Exception as exc:  # noqa: BLE001
            ok = False
            results.append(
                {
                    "module": module_name,
                    "attr": attr,
                    "ok": False,
                    "error": f"{type(exc).__name__}:{exc}",
                }
            )

    # TRAZA router file exists
    traces = ROOT / "apps" / "api" / "routers" / "traces.py"
    results.append({"path": str(traces.relative_to(ROOT)), "ok": traces.is_file()})
    if not traces.is_file():
        ok = False

    report = {"ok": ok, "checks": results}
    out = ROOT / "runtime" / "evals" / "submission_architecture_check.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
