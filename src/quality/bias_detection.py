"""Bias detection helpers."""

from __future__ import annotations

from collections import Counter
from typing import Iterable

from src.schemas.normalized_evidence_schema import NormalizedEvidence


def detect_bias(evidence: Iterable[NormalizedEvidence]) -> list[dict[str, object]]:
    items = list(evidence)
    if not items:
        return []
    source_type_counts = Counter(item.source_type for item in items)
    company_counts = Counter(company for item in items for company in (item.company or ["unattributed"]))
    total = len(items)
    flags: list[dict[str, object]] = []
    dominant_source_type, dominant_source_count = source_type_counts.most_common(1)[0]
    if dominant_source_count / total >= 0.6:
        flags.append(
            {
                "type": "source_type_bias",
                "source_type": dominant_source_type,
                "share": dominant_source_count / total,
            }
        )
    dominant_company, dominant_company_count = company_counts.most_common(1)[0]
    if dominant_company_count / total >= 0.6:
        flags.append(
            {
                "type": "company_bias",
                "company": dominant_company,
                "share": dominant_company_count / total,
            }
        )
    return flags

