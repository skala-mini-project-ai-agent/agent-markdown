"""Conflict detection helpers."""

from __future__ import annotations

from typing import Iterable

from src.schemas.normalized_evidence_schema import NormalizedEvidence


def detect_conflicts(evidence: Iterable[NormalizedEvidence]) -> list[dict[str, object]]:
    conflicts: list[dict[str, object]] = []
    for item in evidence:
        if item.conflict_candidate or item.counter_signals:
            conflicts.append(
                {
                    "evidence_id": item.evidence_id,
                    "technology": item.technology,
                    "company": item.company,
                    "reason": "counter_signals_present" if item.counter_signals else "conflict_candidate",
                }
            )
    return conflicts

