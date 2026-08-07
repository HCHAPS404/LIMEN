"""Embedding provider stubs and factory helpers."""

from __future__ import annotations

from limen.config.settings import ApplicationSettings
from limen.knowledge.contracts import EmbeddingProvider


class StubEmbeddingProvider:
    """Deterministic bag-of-words style embedding for tests."""

    def __init__(self, dimensions: int = 32) -> None:
        self.dimensions = dimensions

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token in text.lower().split():
            idx = hash(token) % self.dimensions
            vector[idx] += 1.0
        norm = sum(v * v for v in vector) ** 0.5 or 1.0
        return [v / norm for v in vector]


def build_embedding_provider(settings: ApplicationSettings) -> EmbeddingProvider:
    provider = settings.embedding_provider.lower().strip()
    if provider == "stub":
        return StubEmbeddingProvider()
    raise ValueError(
        f"Unsupported EMBEDDING_PROVIDER={settings.embedding_provider!r}. Use 'stub' in foundation."
    )
