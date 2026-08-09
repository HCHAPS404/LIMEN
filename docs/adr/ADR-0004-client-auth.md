# ADR-0004 — Client accounts and session auth

## Status
Accepted

## Context
The charter and `FRONTEND.md` §3 keep "enterprise auth" off the challenge critical path, and the workspace was originally reachable with no sign-in. That assumption held while a single operator drove a single corpus.

The product is now used by more than one clinic, and the knowledge base is the clinical corpus each clinic uploads: discharge protocols, internal instructions, and patient-facing material. With shared, unauthenticated access, one client's uploads would be retrievable inside another client's call, and a deletion could remove a corpus that belongs to somebody else. Retrieval provenance would still be technically correct and clinically wrong.

## Decision
Introduce the smallest authentication that produces per-client data isolation:

- New domain package `limen/auth/`: `Account`, `StoredAccount`, `SessionRecord`, an `AccountRepository` protocol, password hashing, and session tokens. The service depends on the protocol only; SQLite lives in `limen/persistence/repositories/accounts.py`.
- Passwords hashed with `hashlib.scrypt` (standard library, so environment reproduction needs no compiler). Parameters are encoded inside the stored hash and can be raised without invalidating existing accounts.
- Sessions are opaque random tokens; only their SHA-256 digest is persisted, so a database dump cannot be replayed as a live cookie.
- Transport: `POST /api/auth/register`, `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me`, `DELETE /api/auth/me` (permanent account removal; clears the cookie). The token travels in an httpOnly, `SameSite=Lax` cookie (`Secure` controlled by `AUTH_COOKIE_SECURE`), never in a response body.
- `apps/api/dependencies.require_account` is the guard every client-owned route must depend on, scoping its queries to `account.account_id`. `/health` stays public so a cold deployment can be probed before any account exists.
- Frontend: `/`, `/login`, and `/register` are public; every workspace surface sits behind `RequireAuth`.
- Schema version moves from 1 to 2 (`accounts`, `auth_sessions`).

Explicitly out of scope: OAuth/SSO, MFA, hospital RBAC, password reset email, and at-rest encryption beyond password hashing.

## Alternatives considered
- **Keep the workspace open.** Rejected: two clients would share one retrievable corpus, which breaks the provenance guarantee the product sells.
- **A single shared passphrase.** Rejected: gates access without separating data, so the isolation problem stays unsolved.
- **Bearer token in `localStorage`.** Rejected: readable by any injected script, and retrieved documents are untrusted input.
- **`argon2-cffi` / `bcrypt`.** Rejected for now: both add a compiled dependency to a cold start that must stay under 15 minutes. The encoded-parameter hash format leaves the door open to migrate.

## Consequences
- The challenge critical path now begins with a sign-in. The demo login is created by `make bootstrap` from `LIMEN_DEMO_EMAIL` / `LIMEN_DEMO_PASSWORD` in `.env.example`, so a cold start still reaches a voice call without manual account setup. Those values are local demo defaults, not deployment credentials.
- Login errors never distinguish "unknown email" from "wrong password", so the form cannot be used to enumerate accounts.
- Knowledge, calls, and traces must carry `account_id` as they are wired to the API. The contract exists now; there is no client-owned route to filter yet beyond `/api/auth/me`.
- Sessions expire after `AUTH_SESSION_TTL_HOURS` (default 168) and expired rows are purged at API boot.

## Challenge impact
Does not alter voice interaction, retrieval, safety decisions, or telemetry. It adds one screen before the workspace and makes per-client corpus isolation an enforceable property rather than a convention.

## Verification
- `tests/unit/test_auth_passwords.py` — salting, verification, malformed hashes.
- `tests/unit/test_auth_service.py` — register/login/logout/delete/expiry, duplicate email, non-enumerable failures, idempotent seed.
- `tests/unit/test_auth_repository.py` — SQLite round trip, account cascade, session purge.
- `tests/integration/test_auth_api.py` — endpoint round trip, delete account, httpOnly cookie flags, error codes, `/health` still public.
- `apps/web/src/app/router/routes.test.tsx` — visitors are redirected to sign in; the account menu appears once a session exists.
