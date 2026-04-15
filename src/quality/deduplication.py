"""Deduplication helpers."""

from __future__ import annotations

from typing import Iterable

from src.retrieval.evidence_retriever import cosine_similarity
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
        if _is_semantic_duplicate(item, deduped):
            removed.append(item.evidence_id)
            continue
        seen.add(key)
        deduped.append(item)
    return deduped, removed


def _is_semantic_duplicate(candidate: NormalizedEvidence, existing: list[NormalizedEvidence]) -> bool:
    vector = candidate.metadata.get("embedding", [])
    if not vector:
        return False
    for item in existing:
        if item.technology != candidate.technology:
            continue
        if sorted(item.company) != sorted(candidate.company):
            continue
        if cosine_similarity(vector, item.metadata.get("embedding", [])) >= 0.97:
            candidate.metadata["near_duplicate_of"] = item.evidence_id
            return True
    return False
