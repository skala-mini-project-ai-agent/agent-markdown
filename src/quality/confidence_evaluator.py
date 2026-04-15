"""Confidence evaluation helpers."""

from __future__ import annotations

from collections import Counter
from typing import Iterable

from src.schemas.normalized_evidence_schema import NormalizedEvidence


CONFIDENCE_ORDER = {"high": 3, "medium": 2, "low": 1}


def evaluate_low_confidence_cells(
    evidence: Iterable[NormalizedEvidence],
    *,
    threshold: int = 2,
) -> list[dict[str, object]]:
    buckets: dict[tuple[str, str], list[NormalizedEvidence]] = {}
    for item in evidence:
        for company in (item.company or ["unattributed"]):
            buckets.setdefault((item.technology, company), []).append(item)
    low_cells: list[dict[str, object]] = []
    for (technology, company), items in buckets.items():
        confidence_counts = Counter(item.confidence for item in items)
        avg_score = sum(CONFIDENCE_ORDER.get(item.confidence, 2) for item in items) / len(items)
        source_diversity = len({item.source_name for item in items if item.source_name})
        direct_count = sum(1 for item in items if item.signal_type == "direct")
        indirect_count = sum(1 for item in items if item.signal_type == "indirect")
        if len(items) < threshold:
            continue
        if avg_score < 2 or direct_count == 0 or source_diversity < 2:
            low_cells.append(
                {
                    "technology": technology,
                    "company": company,
                    "count": len(items),
                    "average_confidence": avg_score,
                    "confidence_counts": dict(confidence_counts),
                    "source_diversity": source_diversity,
                    "direct_count": direct_count,
                    "indirect_count": indirect_count,
                }
            )
    return low_cells
