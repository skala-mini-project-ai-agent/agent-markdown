"""Canonical normalized evidence schema shared with analysis/report stages."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class NormalizedEvidence:
    evidence_id: str
    run_id: str
    agent_type: str
    technology: str
    company: list[str]
    title: str
    source_type: str
    signal_type: str
    source_name: str
    published_at: str
    url: str
    raw_content: str
    key_points: list[str] = field(default_factory=list)
    signals: list[str] = field(default_factory=list)
    counter_signals: list[str] = field(default_factory=list)
    confidence: str = "medium"
    quality_passed: bool = False
    conflict_candidate: bool = False
    unresolved: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    missing_field_flags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

