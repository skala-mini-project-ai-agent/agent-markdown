"""Source diversity helpers."""

from __future__ import annotations

from collections import Counter
from typing import Iterable

from src.schemas.normalized_evidence_schema import NormalizedEvidence


def evaluate_source_diversity(evidence: Iterable[NormalizedEvidence]) -> dict[str, object]:
    items = list(evidence)
    source_types = Counter(item.source_type for item in items)
    source_names = Counter(item.source_name for item in items)
    return {
        "source_type_counts": dict(source_types),
        "source_name_counts": dict(source_names),
        "unique_source_types": len(source_types),
        "unique_source_names": len(source_names),
    }

