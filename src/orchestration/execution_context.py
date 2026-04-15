"""Execution context helpers used by the supervisor."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..agents.base.base_agent import SearchExecutionContext


@dataclass(slots=True)
class SupervisorExecutionContext:
    run_id: str
    user_query: str
    technology_axes: list[str]
    seed_competitors: list[str]
    output_format: str = "markdown"
    freshness_start_year: int = 2024
    open_exploration_mode: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_search_context(self) -> SearchExecutionContext:
        return SearchExecutionContext(
            run_id=self.run_id,
            user_query=self.user_query,
            technology_axes=list(self.technology_axes),
            seed_competitors=list(self.seed_competitors),
            freshness_start_year=self.freshness_start_year,
            open_exploration_mode=self.open_exploration_mode,
            metadata=dict(self.metadata),
        )
