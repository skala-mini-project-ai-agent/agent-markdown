"""Coverage matrix helpers."""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from src.schemas.normalized_evidence_schema import NormalizedEvidence


def build_coverage_matrix(evidence: Iterable[NormalizedEvidence]) -> dict[str, dict[str, int]]:
    matrix: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for item in evidence:
        companies = item.company or ["unattributed"]
        for company in companies:
            matrix[item.technology][company] += 1
    return {technology: dict(companies) for technology, companies in matrix.items()}


def count_cells_below_threshold(
    evidence: Iterable[NormalizedEvidence],
    *,
    threshold: int = 2,
) -> list[dict[str, object]]:
    matrix = build_coverage_matrix(evidence)
    low_cells: list[dict[str, object]] = []
    for technology, companies in matrix.items():
        for company, count in companies.items():
            if count < threshold:
                low_cells.append(
                    {
                        "technology": technology,
                        "company": company,
                        "count": count,
                        "threshold": threshold,
                    }
                )
    return low_cells

