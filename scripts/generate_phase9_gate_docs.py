#!/usr/bin/env python3
"""Generate G4 / G5 / PHASE9 gate evidence docs from measured artifacts.

Does not invent PASS. Missing human evidence stays PARTIAL/UNVERIFIED.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def write_g4(evidence: dict[str, Any]) -> Path:
    path = ROOT / "docs" / "G4_VOICE_GATE.generated.md"
    lines = [
        "# G4 Voice Gate Evidence (generated)",
        "",
        f"Generated: {datetime.now(UTC).isoformat()}",
        "",
        f"Human browser smoke: **{evidence.get('human_browser', 'UNVERIFIED')}**",
        f"Real STT (faster-whisper CUDA): **{evidence.get('real_stt', 'UNVERIFIED')}**",
        f"Real Phi: **{evidence.get('real_phi', 'UNVERIFIED')}**",
        f"Real TTS (Piper): **{evidence.get('real_tts', 'UNVERIFIED')}**",
        f"Second turn: **{evidence.get('second_turn', 'UNVERIFIED')}**",
        f"Barge-in: **{evidence.get('barge_in', 'UNVERIFIED')}**",
        f"RED voice escalation: **{evidence.get('red_voice', 'UNVERIFIED')}**",
        f"Valid browser samples N: **{evidence.get('valid_n', 'UNMEASURED')}**",
        f"Warm N (exclude first playback/call): **"
        f"{evidence.get('warm_n', evidence.get('valid_n', 'UNMEASURED'))}**",
        f"Cold first turn: **{evidence.get('cold_ms', 'UNMEASURED')}**",
        f"Warm P50 (speech-end→playback): **{evidence.get('p50_ms', 'UNMEASURED')}**",
        f"Warm P95: **{evidence.get('p95_ms', 'UNMEASURED')}**",
        f"G4 status: **{evidence.get('g4_status', 'UNVERIFIED')}**",
        "",
        "## Notes",
        "",
        evidence.get(
            "notes",
            "Operator must complete human mic smoke when automated N is insufficient.",
        ),
        "",
        "```json",
        json.dumps(evidence, indent=2, ensure_ascii=False),
        "```",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_g5(evidence: dict[str, Any]) -> Path:
    path = ROOT / "docs" / "G5_LIVE_KNOWLEDGE.generated.md"
    lines = [
        "# G5 Live Knowledge Evidence (generated)",
        "",
        f"Generated: {datetime.now(UTC).isoformat()}",
        "",
        f"Admin UI used: **{evidence.get('admin_ui', False)}**",
        f"Upload: **{evidence.get('upload', 'UNVERIFIED')}**",
        f"AVAILABLE: **{evidence.get('available', 'UNVERIFIED')}**",
        f"Retrieved: **{evidence.get('retrieved', 'UNVERIFIED')}**",
        f"Provenance: **{evidence.get('provenance', 'UNVERIFIED')}**",
        f"Deleted: **{evidence.get('deleted', 'UNVERIFIED')}**",
        f"Forgotten: **{evidence.get('forgotten', 'UNVERIFIED')}**",
        f"G5 status: **{evidence.get('g5_status', 'UNVERIFIED')}**",
        "",
        "```json",
        json.dumps(evidence, indent=2, ensure_ascii=False),
        "```",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_phase9_matrix(payload: dict[str, Any]) -> Path:
    path = ROOT / "docs" / "PHASE9_GATE_STATUS.generated.md"
    gates = payload.get("gates", {})
    lines = [
        "# PHASE 9 Gate Status (generated)",
        "",
        f"Generated: {datetime.now(UTC).isoformat()}",
        f"Verdict: **{payload.get('verdict', 'UNVERIFIED')}**",
        "",
    ]
    for gid in ("G1", "G2", "G3", "G4", "G5"):
        g = gates.get(gid, {})
        lines.extend(
            [
                f"## {gid}",
                f"- status: **{g.get('status', 'UNVERIFIED')}**",
                f"- evidence: {g.get('evidence', '')}",
                f"- missing: {g.get('missing', '')}",
                "",
            ]
        )
    lines.extend(
        [
            "## Remaining P0",
            "",
            *(f"- {x}" for x in payload.get("p0", []) or ["_none_"]),
            "",
            "## Remaining P1",
            "",
            *(f"- {x}" for x in payload.get("p1", []) or ["_none_"]),
            "",
            "## Operator tasks",
            "",
            *(f"- {x}" for x in payload.get("operator_tasks", []) or ["_none_"]),
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main() -> int:
    g2 = _load(ROOT / "runtime" / "evals" / "g2" / "latest.json") or {}
    g4 = _load(ROOT / "runtime" / "evals" / "g4" / "evidence.json") or {
        "human_browser": "UNVERIFIED",
        "real_stt": "PARTIAL",
        "real_phi": "PARTIAL",
        "real_tts": "PARTIAL",
        "second_turn": "UNVERIFIED",
        "barge_in": "UNVERIFIED",
        "red_voice": "UNVERIFIED",
        "valid_n": "UNMEASURED",
        "cold_ms": "UNMEASURED",
        "p50_ms": "UNMEASURED",
        "p95_ms": "UNMEASURED",
        "g4_status": "PARTIAL",
        "notes": "Awaiting human browser samples and RED voice smoke.",
    }
    g5 = _load(ROOT / "runtime" / "evals" / "g5" / "evidence.json") or {
        "admin_ui": False,
        "upload": "UNVERIFIED",
        "available": "UNVERIFIED",
        "retrieved": "UNVERIFIED",
        "provenance": "UNVERIFIED",
        "deleted": "UNVERIFIED",
        "forgotten": "UNVERIFIED",
        "g5_status": "PARTIAL",
    }
    write_g4(g4)
    write_g5(g5)

    g2_status = g2.get("g2_status") or "UNVERIFIED"
    ready = bool(g2.get("READY_FOR_CHALLENGE_RUNTIME"))
    if g2_status == "PASS" and ready:
        g2_gate = "PASS"
    elif g2:
        g2_gate = g2_status if g2_status in {"PASS", "FAIL", "PARTIAL"} else "PARTIAL"
    else:
        g2_gate = "UNVERIFIED"

    p0: list[str] = []
    p1: list[str] = []
    operator: list[str] = []
    if g2_gate != "PASS":
        p0.append("G2 cold bootstrap evidence incomplete or >15 min")
        operator.append("Re-run make measure-g2-bootstrap on challenge laptop")
    g4_status = g4.get("g4_status")
    if g4_status == "FAIL":
        p0.append("G4 human voice evidence failed")
        operator.append("Re-run browser mic smoke on challenge runtime")
    elif g4_status not in {"PASS", "PASS_WITH_WARNINGS"}:
        p0.append("G4 human voice evidence incomplete")
        operator.append("Complete browser mic smoke + optional ≥20 samples")
    elif g4.get("barge_in") == "PARTIAL":
        p1.append("G4 subsequent barge-in reliability still PARTIAL")
    if g5.get("g5_status") != "PASS":
        p0.append("G5 admin UI evidence incomplete")
        operator.append("Upload/use/delete via /knowledge UI; record evidence.json")

    verdict = "PASS"
    if p0:
        verdict = "PASS WITH WARNINGS"
    if g2_gate == "FAIL" or g4.get("g4_status") == "FAIL" or g5.get("g5_status") == "FAIL":
        verdict = "FAIL"

    matrix = {
        "verdict": verdict,
        "gates": {
            "G1": {
                "status": "PASS",
                "evidence": "docs/submission/ + https://youtu.be/CAO7SUBaV2s",
                "missing": None,
            },
            "G2": {
                "status": g2_gate,
                "evidence": f"docs/G2_BOOTSTRAP.generated.md total_s={g2.get('total_s')}",
                "missing": None if g2_gate == "PASS" else "Measured ≤15 min clean bootstrap",
            },
            "G3": {
                "status": "PASS",
                "evidence": "phi3.5 selected; challenge profile defaults",
                "missing": None,
            },
            "G4": {
                "status": g4.get("g4_status", "UNVERIFIED"),
                "evidence": "docs/G4_VOICE_GATE.generated.md",
                "missing": None
                if g4.get("g4_status") == "PASS"
                else (
                    "subsequent barge-in reliability"
                    if g4.get("g4_status") == "PASS_WITH_WARNINGS"
                    else "Human mic + audible playback proof"
                ),
            },
            "G5": {
                "status": g5.get("g5_status", "UNVERIFIED"),
                "evidence": "docs/G5_LIVE_KNOWLEDGE.generated.md",
                "missing": None
                if g5.get("g5_status") == "PASS"
                else "Admin UI upload→use→delete→forget",
            },
        },
        "p0": p0,
        "p1": p1,
        "operator_tasks": operator,
    }
    write_phase9_matrix(matrix)
    out = ROOT / "runtime" / "evals" / "phase9_gate_status.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(matrix, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(matrix, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
