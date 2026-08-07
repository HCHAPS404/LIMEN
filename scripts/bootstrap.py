#!/usr/bin/env python3
"""Create runtime directories and initialize SQLite."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from limen.config.settings import get_settings
from limen.persistence.database import Database


def main() -> int:
    settings = get_settings()
    settings.ensure_runtime_dirs()
    db = Database(settings.database_path)
    db.initialize()
    db.close()
    print(f"Bootstrap complete. Database: {settings.database_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
