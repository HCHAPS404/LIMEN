"""Reciprocal Rank Fusion for hybrid retrieval."""

from __future__ import annotations

from limen.knowledge.contracts import EvidenceChunk


def reciprocal_rank_fusion(
    ranked_lists: list[list[EvidenceChunk]],
    *,
    k: int = 60,
    limit: int = 5,
) -> list[EvidenceChunk]:
    """Combine ranked evidence lists with RRF. Score scales need not match."""
    scores: dict[str, float] = {}
    best: dict[str, EvidenceChunk] = {}
    modes: dict[str, set[str]] = {}

    for ranked in ranked_lists:
        for rank, chunk in enumerate(ranked, start=1):
            key = chunk.chunk_id
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank)
            prior_modes = set(chunk.retrieval_modes)
            if key not in best or len(chunk.text) > len(best[key].text):
                best[key] = chunk
            modes.setdefault(key, set()).update(prior_modes)

    ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    fused: list[EvidenceChunk] = []
    for chunk_id, score in ordered[:limit]:
        chunk = best[chunk_id].model_copy(deep=True)
        chunk.score = score
        chunk.retrieval_modes = sorted(modes.get(chunk_id, set()))
        fused.append(chunk)
    return fused
