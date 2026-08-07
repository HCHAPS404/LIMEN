# ADR-0003 — Provider contracts

## Status
Accepted

## Context
Runtime LLM/STT/TTS/embeddings must be replaceable without rewriting clinical, safety, RAG, or persistence layers. Competition model rules may change.

## Decision
Define Protocol contracts in domain packages and confine vendor SDKs to adapter modules. Default development providers are stubs; Ollama is available for local LLM.

## Alternatives considered
- Direct SDK imports in domain code — rejected (couples product to vendor).
- Single hard-coded cloud provider — rejected (non-compliant if rules change).

## Consequences
Factory selection via settings; CI boundary check blocks leaked imports.

## Challenge impact
Satisfies G3 (provider-isolated runtime LLM).

## Verification
`tests/contract/test_providers.py` and `scripts/check_boundaries.py`.
