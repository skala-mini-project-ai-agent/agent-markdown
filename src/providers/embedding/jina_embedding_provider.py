"""Jina Embeddings API provider."""

from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .base_embedding_provider import BaseEmbeddingProvider


@dataclass(slots=True)
class JinaEmbeddingProvider(BaseEmbeddingProvider):
    api_key: str
    model: str = "jina-embeddings-v4"
    endpoint: str = "https://api.jina.ai/v1/embeddings"
    batch_size: int = 4
    max_chars: int = 1500

    def embed_texts(self, texts: list[str], *, task: str = "retrieval") -> list[list[float]]:
        resolved_task = self._resolve_task(task)
        sanitized = [self._sanitize_text(text) for text in texts]
        vectors: list[list[float]] = []
        for start in range(0, len(sanitized), self.batch_size):
            batch = sanitized[start : start + self.batch_size]
            payload = {
                "model": self.model,
                "task": resolved_task,
                "embedding_type": "float",
                "normalized": True,
                "input": batch,
            }
            request = Request(
                self.endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "content-type": "application/json",
                    "authorization": f"Bearer {self.api_key}",
                    "accept": "application/json",
                    "user-agent": "curl/8.7.1",
                },
                method="POST",
            )
            try:
                with urlopen(request, timeout=30) as response:
                    data = json.loads(response.read().decode("utf-8"))
            except HTTPError as exc:  # pragma: no cover - network path
                detail = exc.read().decode("utf-8", errors="replace")
                raise RuntimeError(f"Jina embedding failed: HTTP {exc.code}: {detail}") from exc
            except URLError as exc:  # pragma: no cover - network path
                raise RuntimeError(f"Jina embedding failed: {exc}") from exc

            items = data.get("data") or []
            vectors.extend(list(item.get("embedding") or []) for item in items)
        return vectors

    def _resolve_task(self, task: str) -> str:
        mapping = {
            "retrieval": "retrieval.passage",
            "retrieval.passage": "retrieval.passage",
            "retrieval.query": "retrieval.query",
            "text-matching": "text-matching",
            "code.query": "code.query",
            "code.passage": "code.passage",
        }
        return mapping.get(task, "retrieval.passage")

    def _sanitize_text(self, text: str) -> str:
        compact = " ".join((text or "").split())
        if len(compact) <= self.max_chars:
            return compact
        head = compact[: self.max_chars // 2]
        tail = compact[-(self.max_chars // 2) :]
        return f"{head} ... {tail}"
