#!/usr/bin/env python3
"""Export submission Mermaid diagrams to PNG under docs/submission/assets/.

Requires Node + @mermaid-js/mermaid-cli (npx). Does not invent diagrams:
source remains the Markdown files in docs/submission/.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs" / "submission" / "assets"
FENCE = re.compile(r"```mermaid\n(.*?)```", re.DOTALL)

EXPORTS = (
    ("ARCHITECTURE.md", 0, "architecture.png"),
    ("DECISION_FLOW.md", 0, "decision_flow.png"),
    ("KNOWLEDGE_FLOW.md", 0, "knowledge_ingest.png"),
    ("KNOWLEDGE_FLOW.md", 1, "knowledge_forget.png"),
    ("TRAZA.md", 0, "traza_turn.png"),
)


def _extract(md_path: Path) -> list[str]:
    text = md_path.read_text(encoding="utf-8")
    return [match.group(1).strip() + "\n" for match in FENCE.finditer(text)]


def _puppeteer_config(tmp_path: Path) -> Path | None:
    chrome = (
        shutil.which("google-chrome-stable")
        or shutil.which("google-chrome")
        or shutil.which("chromium")
    )
    if not chrome:
        return None
    config = tmp_path / "puppeteer.json"
    config.write_text(
        json.dumps(
            {
                "executablePath": chrome,
                "args": ["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
            }
        ),
        encoding="utf-8",
    )
    return config


def _mmdc() -> list[str]:
    found = shutil.which("mmdc")
    if found:
        return [found]
    return ["npx", "--yes", "@mermaid-js/mermaid-cli"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-render", action="store_true")
    args = parser.parse_args()

    ASSETS.mkdir(parents=True, exist_ok=True)
    cmd = _mmdc()
    with tempfile.TemporaryDirectory(prefix="limen-mermaid-") as tmp:
        tmp_path = Path(tmp)
        puppeteer = _puppeteer_config(tmp_path)
        for filename, index, png_name in EXPORTS:
            source = ROOT / "docs" / "submission" / filename
            blocks = _extract(source)
            if index >= len(blocks):
                print(f"missing mermaid block {index} in {filename}", file=sys.stderr)
                return 2
            mmd = tmp_path / f"{Path(png_name).stem}.mmd"
            mmd.write_text(blocks[index], encoding="utf-8")
            out = ASSETS / png_name
            if args.skip_render:
                (ASSETS / f"{Path(png_name).stem}.mmd").write_text(blocks[index], encoding="utf-8")
                print(f"Wrote {ASSETS / f'{Path(png_name).stem}.mmd'}")
                continue
            render = [
                *cmd,
                "-i",
                str(mmd),
                "-o",
                str(out),
                "-b",
                "transparent",
                "-s",
                "2",
            ]
            if puppeteer is not None:
                render.extend(["-p", str(puppeteer)])
            print(" ".join(render))
            proc = subprocess.run(render, cwd=ROOT, check=False)
            if proc.returncode != 0:
                return proc.returncode
            print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
