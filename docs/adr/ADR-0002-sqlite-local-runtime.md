# ADR-0002 — SQLite local runtime

## Status
Accepted

## Context
Challenge prefers minimum operational complexity and reproducible local setup.

## Decision
Use SQLite at `./runtime/db/limen.db` with filesystem dirs under `runtime/` (gitignored) for documents, vectors, audio, and logs.

## Alternatives considered
- Managed cloud Postgres — unnecessary for challenge critical path.
- In-memory only — loses session durability for demos/evals.

## Consequences
Zero external DB provisioning; runtime artifacts never committed.

## Challenge impact
Cold-start stays local and deterministic.

## Verification
`scripts/bootstrap.py` initializes schema; `/health` reports database status.
