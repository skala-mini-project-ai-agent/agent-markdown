"""Common agent utilities."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class SearchExecutionContext:
    run_id: str
    user_query: str = ""
    technology_axes: list[str] = field(default_factory=list)
    seed_competitors: list[str] = field(default_factory=list)
    freshness_start_year: int = 2024
    open_exploration_mode: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "user_query": self.user_query,
            "technology_axes": list(self.technology_axes),
            "seed_competitors": list(self.seed_competitors),
            "freshness_start_year": self.freshness_start_year,
            "open_exploration_mode": self.open_exploration_mode,
            "metadata": dict(self.metadata),
        }


@dataclass(slots=True)
class AgentValidationResult:
    passed: bool
    summary: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


class BaseAgent:
    agent_type: str = "base"

    def __init__(self, *, provider: Any | None = None) -> None:
        self.provider = provider

