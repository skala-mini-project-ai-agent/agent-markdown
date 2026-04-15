"""Strategic overlap rules for SK hynix focused threat analysis."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class StrategicOverlapProfile:
    technology: str
    company: str
    score: int
    rationale: str
    assumptions: tuple[str, ...]


_TECHNOLOGY_BASE_SCORES = {
    "hbm4": 5,
    "pim": 4,
    "cxl": 3,
    "advanced packaging": 5,
    "packaging": 5,
    "thermal": 4,
    "thermal power": 4,
    "thermal·power": 4,
}

_HIGH_OVERLAP_COMPANIES = {
    "samsung",
    "micron",
    "nvidia",
    "amd",
    "intel",
    "tsmc",
    "ase",
    "skhynix",
    "sk hynix",
}


def _normalize(text: str) -> str:
    return " ".join(text.lower().replace("·", " ").replace("-", " ").split())


def _match_technology_score(technology: str) -> int:
    normalized = _normalize(technology)
    for key, score in _TECHNOLOGY_BASE_SCORES.items():
        if key in normalized:
            return score
    return 3


def _match_company_adjustment(company: str) -> int:
    normalized = _normalize(company)
    if any(token in normalized for token in _HIGH_OVERLAP_COMPANIES):
        return 0
    if "startup" in normalized or "research" in normalized:
        return -1
    return 0


def get_strategic_overlap_profile(technology: str, company: str) -> StrategicOverlapProfile:
    base = _match_technology_score(technology)
    adjustment = _match_company_adjustment(company)
    score = max(1, min(5, base + adjustment))
    assumptions = (
        "SK hynix strategic overlap is estimated from technology-domain relevance.",
        "Overlap is treated as a company-facing execution and roadmap proximity heuristic.",
    )
    rationale = f"{technology} is treated as a {score}/5 overlap domain for {company}."
    return StrategicOverlapProfile(
        technology=technology,
        company=company,
        score=score,
        rationale=rationale,
        assumptions=assumptions,
    )


def get_strategic_overlap_score(technology: str, company: str) -> int:
    return get_strategic_overlap_profile(technology, company).score


def overlap_assumptions() -> tuple[str, ...]:
    return (
        "High overlap means the target technology could affect SK hynix roadmap, supply chain, or product differentiation.",
        "Low overlap means the technology remains relevant but less directly tied to near-term execution risk.",
    )

