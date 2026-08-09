#!/usr/bin/env python3
"""Create runtime directories, initialize SQLite, and seed the demo account."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from limen.auth import AuthService
from limen.config.settings import get_settings
from limen.persistence.database import Database
from limen.persistence.repositories import SqliteAccountRepository


def main() -> int:
    settings = get_settings()
    settings.ensure_runtime_dirs()
    db = Database(settings.database_path)
    db.initialize()

    if settings.has_demo_account():
        # Idempotent: an existing account keeps its current password.
        account = AuthService(
            SqliteAccountRepository(db),
            session_ttl=settings.auth_session_ttl(),
        ).ensure_account(
            settings.demo_email,
            settings.demo_password,
            settings.demo_display_name,
        )
        print(f"Demo account ready: {account.email}")
    else:
        print("No demo account configured (set LIMEN_DEMO_EMAIL and LIMEN_DEMO_PASSWORD).")

    db.close()
    print(f"Bootstrap complete. Database: {settings.database_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
