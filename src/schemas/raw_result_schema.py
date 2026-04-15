"""Raw search result schema for search owner outputs."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class SearchQuery:
    query: str
    technology: str
    source_hints: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RawFinding:
    raw_finding_id: str
    run_id: str
    agent_type: str
    query: str
    title: str
    source_type: str
    signal_type: str
    source_name: str
    published_at: str
    url: str
    raw_content: str
    key_points: list[str] = field(default_factory=list)
    company: list[str] = field(default_factory=list)
    technology: str = ""
    signals: list[str] = field(default_factory=list)
    counter_signals: list[str] = field(default_factory=list)
    confidence: str = "medium"
    metadata: dict[str, Any] = field(default_factory=dict)
    missing_field_flags: list[str] = field(default_factory=list)
    local_validation: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RawSearchBundle:
    run_id: str
    agent_type: str
    executed_at: str
    queries: list[SearchQuery] = field(default_factory=list)
    raw_findings: list[RawFinding] = field(default_factory=list)
    local_validation: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["queries"] = [asdict(query) for query in self.queries]
        payload["raw_findings"] = [finding.to_dict() for finding in self.raw_findings]
        return payload

