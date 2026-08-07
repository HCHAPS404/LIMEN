"""Evidence provenance helpers — Planned beyond foundation."""

from limen.knowledge.contracts import EvidenceChunk


def format_citation(chunk: EvidenceChunk) -> str:
    page = f", p.{chunk.page}" if chunk.page is not None else ""
    return f"{chunk.source_name}{page} [{chunk.chunk_id}]"
