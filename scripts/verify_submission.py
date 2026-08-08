#!/usr/bin/env python3
"""Foundation submission gate checks."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    checks: list[tuple[str, bool]] = []

    checks.append(("MIT LICENSE", (ROOT / "LICENSE").exists()))
    checks.append(("README", (ROOT / "README.md").exists()))
    checks.append(("ARCHITECTURE", (ROOT / "ARCHITECTURE.md").exists()))
    checks.append(("AGENTS.md", (ROOT / "AGENTS.md").exists()))
    checks.append(("BACKEND.md", (ROOT / "BACKEND.md").exists()))
    checks.append(("FRONTEND.md", (ROOT / "FRONTEND.md").exists()))
    checks.append((".env.example", (ROOT / ".env.example").exists()))
    checks.append(("Makefile", (ROOT / "Makefile").exists()))
    checks.append(("pyproject.toml", (ROOT / "pyproject.toml").exists()))
    checks.append(("API main", (ROOT / "apps" / "api" / "main.py").exists()))
    checks.append(("Web package", (ROOT / "apps" / "web" / "package.json").exists()))
    checks.append(("ADR folder", (ROOT / "docs" / "adr").is_dir()))
    gitignore = (ROOT / ".gitignore").read_text()
    checks.append((".gitignore excludes runtime", "runtime/" in gitignore))
    checks.append((".gitignore excludes local tooling", ".cursor/" in gitignore))

    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        mark = "PASS" if ok else "FAIL"
        print(f"[{mark}] {name}")

    if failed:
        print(f"\nSubmission foundation FAILED ({len(failed)} checks)")
        return 1

    print("\nSubmission foundation PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
