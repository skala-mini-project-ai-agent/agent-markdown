"""No-op embedding provider placeholder until a real embedding backend is configured."""

from __future__ import annotations

from .base_embedding_provider import BaseEmbeddingProvider


class NoopEmbeddingProvider(BaseEmbeddingProvider):
    def embed_texts(self, texts: list[str], *, task: str = "retrieval") -> list[list[float]]:
        return [[0.0] for _ in texts]
