"""Deduplication helpers."""

from __future__ import annotations

from typing import Iterable

from src.schemas.normalized_evidence_schema import NormalizedEvidence


def deduplicate_evidence(evidence: Iterable[NormalizedEvidence]) -> tuple[list[NormalizedEvidence], list[str]]:
    seen: set[tuple[str, str, tuple[str, ...]]] = set()
    deduped: list[NormalizedEvidence] = []
    removed: list[str] = []
    for item in evidence:
        key = (item.url, item.title.lower(), tuple(item.company))
        if key in seen:
            removed.append(item.evidence_id)
            continue
        seen.add(key)
        deduped.append(item)
    return deduped, removed

