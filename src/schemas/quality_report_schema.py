"""Canonical quality report schema for downstream stages."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class QualityReport:
    run_id: str
    status: str
    coverage: dict[str, Any] = field(default_factory=dict)
    source_diversity: dict[str, Any] = field(default_factory=dict)
    duplicates_removed: list[str] = field(default_factory=list)
    bias_flags: list[dict[str, Any]] = field(default_factory=list)
    conflict_flags: list[dict[str, Any]] = field(default_factory=list)
    low_evidence_cells: list[dict[str, Any]] = field(default_factory=list)
    low_confidence_cells: list[dict[str, Any]] = field(default_factory=list)
    retry_recommendations: list[dict[str, Any]] = field(default_factory=list)
    analysis_ready: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

