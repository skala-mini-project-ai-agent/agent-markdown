"""Embedding-aware evidence retrieval helpers."""

from __future__ import annotations

import math
import re
from typing import Iterable, Sequence

from src.schemas.analysis_output_schema import MergedAnalysisResult
from src.schemas.normalized_evidence_schema import NormalizedEvidence


def build_evidence_text(evidence: NormalizedEvidence) -> str:
    return "\n".join(
        [
            f"Title: {evidence.title}",
            f"Technology: {evidence.technology}",
            f"Company: {', '.join(evidence.company)}",
            f"Source Type: {evidence.source_type}",
            f"Signal Type: {evidence.signal_type}",
            f"Key Points: {' | '.join(evidence.key_points)}",
            f"Signals: {' | '.join(evidence.signals)}",
            f"Counter Signals: {' | '.join(evidence.counter_signals)}",
            f"Content: {evidence.raw_content}",
        ]
    )


def build_claim_text(item: MergedAnalysisResult) -> str:
    return "\n".join(
        [
            f"Technology: {item.technology}",
            f"Company: {item.company}",
            f"TRL: {item.trl_range}",
            f"Threat: {item.threat_level.value}",
            f"Priority: {item.priority_bucket.value}",
            f"Action: {item.action_hint}",
            f"Notes: {' | '.join(item.notes)}",
        ]
    )


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot / (left_norm * right_norm)


def attach_embeddings(
    evidence_items: list[NormalizedEvidence],
    *,
    embedding_provider: object | None,
    task: str = "retrieval",
) -> list[NormalizedEvidence]:
    if embedding_provider is None or not evidence_items or not hasattr(embedding_provider, "embed_texts"):
        return evidence_items
    texts = [build_evidence_text(item) for item in evidence_items]
    vectors = embedding_provider.embed_texts(texts, task=task)
    for item, vector in zip(evidence_items, vectors):
        item.metadata["embedding"] = vector
    return evidence_items


def top_k_similar_evidence(
    query_vector: Sequence[float],
    evidence_items: Iterable[NormalizedEvidence],
    *,
    technology: str | None = None,
    company: str | None = None,
    top_k: int = 3,
) -> list[tuple[NormalizedEvidence, float]]:
    ranked: list[tuple[NormalizedEvidence, float]] = []
    for item in evidence_items:
        if technology and item.technology != technology:
            continue
        if company and company not in item.company:
            continue
        score = cosine_similarity(query_vector, item.metadata.get("embedding", []))
        ranked.append((item, score))
    ranked.sort(key=lambda entry: entry[1], reverse=True)
    return ranked[:top_k]


def extract_expansion_terms(evidence_items: Iterable[NormalizedEvidence], *, limit: int = 6) -> list[str]:
    text = " ".join(
        " ".join([item.title, *item.key_points, *item.signals, *item.counter_signals])
        for item in evidence_items
    ).lower()
    tokens = re.findall(r"[a-z0-9][a-z0-9\-]{3,}", text)
    stop = {"signal", "update", "roadmap", "technology", "company", "trend", "with", "from", "that", "this"}
    ordered: list[str] = []
    for token in tokens:
        if token in stop or token in ordered:
            continue
        ordered.append(token)
        if len(ordered) >= limit:
            break
    return ordered
