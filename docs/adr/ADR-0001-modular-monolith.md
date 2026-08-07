# ADR-0001 — Modular monolith

## Status
Accepted

## Context
LIMEN must ship a reproducible challenge system with voice, knowledge, safety, and telemetry without infrastructure sprawl.

## Decision
Build a single deployable modular monolith with explicit domain packages under `limen/`.

## Alternatives considered
- Microservices / event brokers — rejected as out of scope and high operational cost.
- Frontend-only demo — rejected; challenge requires working backend flows.

## Consequences
Clear domain boundaries, simpler bootstrap (≤15 minutes), shared SQLite runtime.

## Challenge impact
Supports G2 startup gate and keeps critical path small.

## Verification
Repository layout matches `ARCHITECTURE.md`; API and web boot via Makefile.
