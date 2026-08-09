#!/usr/bin/env python3
"""G5 live-knowledge evidence via authenticated API (admin UI still required for PASS).

When --ui-note is set, records that the operator exercised /knowledge in a browser.
API path alone cannot promote G5 to PASS.
"""

from __future__ import annotations

import argparse
import json
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
FACT = f"LIMEN_P9_G5_FACT_{uuid.uuid4().hex[:10].upper()}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8000")
    parser.add_argument("--email", default=None)
    parser.add_argument("--password", default=None)
    parser.add_argument(
        "--ui-confirmed",
        action="store_true",
        help="Operator confirms the same flow was performed in /knowledge UI",
    )
    args = parser.parse_args()

    email = args.email or "demo@limen.local"
    password = args.password or "limen-demo-2026"
    evidence: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "admin_ui": bool(args.ui_confirmed),
        "mode": "api_assisted",
        "unique_fact": FACT,
    }

    with httpx.Client(base_url=args.base, timeout=120.0) as client:
        login = client.post(
            "/api/auth/login",
            json={"email": email, "password": password},
        )
        if login.status_code >= 400:
            evidence["error"] = f"login_failed:{login.status_code}:{login.text[:200]}"
            _write(evidence)
            return 1

        body = (
            f"# G5 PHASE9 unique document\n\n"
            f"Synthetic fact: {FACT}\n"
            f"Harmless postoperative checklist marker for live knowledge.\n"
        ).encode()
        files = {"file": ("g5_phase9_unique.txt", body, "text/plain")}
        up = client.post("/api/knowledge/documents", files=files)
        evidence["upload"] = "PASS" if up.status_code < 300 else f"FAIL:{up.status_code}"
        if up.status_code >= 300:
            evidence["error"] = up.text[:400]
            _write(evidence)
            return 1
        doc = up.json()
        doc_id = doc.get("document_id")
        evidence["document_id"] = doc_id

        available = False
        status = doc.get("status")
        for _ in range(60):
            listed = client.get("/api/knowledge/documents")
            rows = listed.json() if listed.status_code < 300 else []
            match = next((r for r in rows if r.get("document_id") == doc_id), None)
            status = (match or {}).get("status", status)
            if status == "AVAILABLE":
                available = True
                break
            if status in {"FAILED", "REMOVED"}:
                break
            time.sleep(1)
        evidence["available"] = "PASS" if available else f"FAIL:{status}"

        probe = client.get(
            "/api/knowledge/retrieval-probe",
            params={"query": FACT},
        )
        payload = probe.json() if probe.status_code < 300 else {}
        hits = payload.get("chunks") if isinstance(payload, dict) else []
        if not isinstance(hits, list):
            hits = []
        evidence["retrieved"] = "PASS" if hits else "FAIL"
        if hits:
            h0 = hits[0]
            evidence["provenance"] = {
                "document_id": h0.get("document_id"),
                "chunk_id": h0.get("chunk_id"),
                "source_name": h0.get("source_name") or h0.get("filename"),
                "page": h0.get("page"),
                "matches_upload": h0.get("document_id") == doc_id,
            }
            evidence["provenance_ok"] = bool(h0.get("document_id") == doc_id)
        else:
            evidence["provenance_ok"] = False

        deleted = client.delete(f"/api/knowledge/documents/{doc_id}")
        evidence["deleted"] = "PASS" if deleted.status_code < 300 else f"FAIL:{deleted.status_code}"

        forgotten = False
        for _ in range(40):
            probe2 = client.get(
                "/api/knowledge/retrieval-probe",
                params={"query": FACT},
            )
            payload2 = probe2.json() if probe2.status_code < 300 else {}
            hits2 = payload2.get("chunks") if isinstance(payload2, dict) else []
            if not isinstance(hits2, list):
                hits2 = []
            stale = [h for h in hits2 if h.get("document_id") == doc_id]
            if not stale:
                forgotten = True
                break
            time.sleep(0.5)
        evidence["forgotten"] = "PASS" if forgotten else "FAIL"

    api_ok = all(
        evidence.get(k) == "PASS"
        for k in ("upload", "available", "retrieved", "deleted", "forgotten")
    ) and evidence.get("provenance_ok")

    if args.ui_confirmed and api_ok:
        evidence["g5_status"] = "PASS"
    elif api_ok:
        evidence["g5_status"] = "PARTIAL"
        evidence["missing"] = "Admin UI confirmation (--ui-confirmed) required for G5 PASS"
    else:
        evidence["g5_status"] = "FAIL"

    _write(evidence)
    print(json.dumps(evidence, indent=2, ensure_ascii=False))
    return 0 if evidence["g5_status"] in {"PASS", "PARTIAL"} else 1


def _write(evidence: dict[str, Any]) -> None:
    out = ROOT / "runtime" / "evals" / "g5" / "evidence.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(evidence, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md = ROOT / "docs" / "G5_LIVE_KNOWLEDGE.generated.md"
    lines = [
        "# G5 Live Knowledge Evidence (generated)",
        "",
        f"Generated: {evidence.get('generated_at')}",
        f"Admin UI used: **{evidence.get('admin_ui')}**",
        f"Upload: **{evidence.get('upload')}**",
        f"AVAILABLE: **{evidence.get('available')}**",
        f"Retrieved: **{evidence.get('retrieved')}**",
        f"Provenance: **{evidence.get('provenance')}**",
        f"Deleted: **{evidence.get('deleted')}**",
        f"Forgotten: **{evidence.get('forgotten')}**",
        f"G5 status: **{evidence.get('g5_status')}**",
        "",
        "```json",
        json.dumps(evidence, indent=2, ensure_ascii=False),
        "```",
        "",
    ]
    md.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out} and {md}")


if __name__ == "__main__":
    raise SystemExit(main())
