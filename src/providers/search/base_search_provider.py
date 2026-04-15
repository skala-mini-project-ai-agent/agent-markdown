"""Base interface for search providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from src.schemas.raw_result_schema import RawFinding, SearchQuery


class BaseSearchProvider(ABC):
    @abstractmethod
    def search(
        self,
        query: SearchQuery,
        *,
        run_id: str,
        agent_type: str,
        context: dict[str, Any] | None = None,
    ) -> list[RawFinding]:
        raise NotImplementedError

