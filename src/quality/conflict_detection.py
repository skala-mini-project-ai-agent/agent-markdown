"""Conflict detection helpers."""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from src.schemas.normalized_evidence_schema import NormalizedEvidence


def detect_conflicts(evidence: Iterable[NormalizedEvidence]) -> list[dict[str, object]]:
    buckets: dict[tuple[str, str], dict[str, int]] = defaultdict(lambda: {"positive": 0, "counter": 0})
    sample_ids: dict[tuple[str, str], list[str]] = defaultdict(list)
    for item in evidence:
        companies = item.company or ["unattributed"]
        has_positive = bool(item.signals or item.signal_type == "direct")
        has_counter = bool(item.counter_signals)
        if not (has_positive or has_counter):
            continue
        for company in companies:
            key = (item.technology, company)
            if has_positive:
                buckets[key]["positive"] += 1
            if has_counter:
                buckets[key]["counter"] += 1
            sample_ids[key].append(item.evidence_id)

    conflicts: list[dict[str, object]] = []
    for (technology, company), counts in sorted(buckets.items()):
        if counts["positive"] == 0 or counts["counter"] == 0:
            continue
        conflicts.append(
            {
                "technology": technology,
                "company": company,
                "reason": "opposing_signal_mix",
                "positive_count": counts["positive"],
                "counter_count": counts["counter"],
                "evidence_ids": sample_ids[(technology, company)][:5],
            }
        )
    return conflicts
