"""Storage contract for the auth domain.

The service depends on this protocol only, so SQLite stays an implementation
detail in limen/persistence (ARCHITECTURE.md: cross-domain calls use contracts).
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from limen.auth.models import SessionRecord, StoredAccount


class AccountRepository(Protocol):
    def insert_account(self, account: StoredAccount) -> None: ...

    def find_account_by_email(self, email: str) -> StoredAccount | None: ...

    def find_account_by_id(self, account_id: str) -> StoredAccount | None: ...

    def insert_session(self, session: SessionRecord) -> None: ...

    def find_session(self, token_hash: str) -> SessionRecord | None: ...

    def delete_session(self, token_hash: str) -> None: ...

    def delete_sessions_expired_before(self, moment: datetime) -> int: ...
