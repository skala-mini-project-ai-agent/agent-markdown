"""Base interface for embedding providers."""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseEmbeddingProvider(ABC):
    @abstractmethod
    def embed_texts(self, texts: list[str], *, task: str = "retrieval") -> list[list[float]]:
        raise NotImplementedError
