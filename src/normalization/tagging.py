"""Tagging helpers for normalized evidence."""

from __future__ import annotations

import re
from typing import Any

from src.schemas.raw_result_schema import RawFinding


COMPANY_ALIASES: dict[str, tuple[str, ...]] = {
    "SK hynix": ("sk hynix", "skhynix", "hynix"),
    "Samsung": ("samsung electronics", "samsung"),
    "Micron": ("micron technology", "micron"),
    "TSMC": ("taiwan semiconductor manufacturing", "tsmc"),
    "Intel": ("intel"),
    "NVIDIA": ("nvidia"),
    "AMD": ("advanced micro devices", "amd"),
    "Broadcom": ("broadcom"),
    "Marvell": ("marvell"),
    "Qualcomm": ("qualcomm"),
    "Apple": ("apple"),
    "Amazon": ("amazon web services", "aws", "amazon"),
    "Google": ("google", "alphabet"),
    "Meta": ("meta platforms", "meta"),
    "Microsoft": ("microsoft"),
}


def infer_technology(raw_finding: RawFinding) -> str:
    if raw_finding.technology:
        return raw_finding.technology
    if raw_finding.agent_type == "packaging":
        return "Advanced Packaging"
    if raw_finding.agent_type == "thermal_power":
        return "Thermal·Power"
    if raw_finding.agent_type == "indirect_signal":
        return "Indirect Signal"
    return raw_finding.agent_type.upper()


def infer_company(raw_finding: RawFinding) -> list[str]:
    if raw_finding.company:
        return _unique([str(company) for company in raw_finding.company if str(company)])
    metadata = dict(raw_finding.metadata)
    seed_competitors = metadata.get("seed_competitors", [])
    candidate_names = [str(item) for item in seed_competitors if str(item)]
    return infer_primary_companies(
        title=raw_finding.title,
        query=raw_finding.query,
        raw_content=raw_finding.raw_content,
        source_name=raw_finding.source_name,
        url=raw_finding.url,
        site_name=str(metadata.get("site_name", "")),
        candidates=candidate_names,
    )


def infer_source_type(raw_finding: RawFinding) -> str:
    return raw_finding.source_type or "other"


def build_metadata(raw_finding: RawFinding) -> dict[str, Any]:
    return {
        "agent_type": raw_finding.agent_type,
        "query": raw_finding.query,
        "raw_finding_id": raw_finding.raw_finding_id,
        **dict(raw_finding.metadata),
    }


def extract_companies_from_text(text: str, *, candidates: list[str] | None = None) -> list[str]:
    if not text:
        return []
    normalized_text = text.lower()
    resolved: list[str] = []
    candidate_map = _candidate_map(candidates)
    for canonical, aliases in candidate_map.items():
        if any(_contains_alias(normalized_text, alias) for alias in aliases):
            resolved.append(canonical)
    return _unique(resolved)


def infer_primary_companies(
    *,
    title: str,
    query: str,
    raw_content: str,
    source_name: str,
    url: str,
    site_name: str = "",
    candidates: list[str] | None = None,
) -> list[str]:
    candidate_map = _candidate_map(candidates)
    if not candidate_map:
        return []

    scores = {canonical: 0 for canonical in candidate_map}
    title_matched: set[str] = set()
    query_matched: set[str] = set()
    title_text = title or ""
    query_text = query or ""
    source_text = " ".join(filter(None, [source_name, site_name, url]))
    lead_text = _lead_text(raw_content)

    for canonical, aliases in candidate_map.items():
        title_hits = _field_hit(title_text, aliases)
        query_hits = _field_hit(query_text, aliases)
        source_hits = _field_hit(source_text, aliases)
        lead_hits = _field_hit(lead_text, aliases)
        body_hits = _match_count(raw_content[:4000], aliases)

        score = 0
        score += int(title_hits) * 5
        score += int(query_hits) * 4
        score += int(source_hits) * 3
        score += int(lead_hits) * 2
        if body_hits >= 2:
            score += 2
        elif body_hits == 1 and (title_hits or query_hits):
            score += 1
        scores[canonical] = score
        if title_hits:
            title_matched.add(canonical)
        if query_hits:
            query_matched.add(canonical)

    ranked = [(canonical, score) for canonical, score in scores.items() if score > 0]
    ranked.sort(key=lambda item: (-item[1], item[0]))
    if not ranked:
        return []

    if title_matched:
        ranked = [item for item in ranked if item[0] in title_matched]
    elif query_matched:
        ranked = [item for item in ranked if item[0] in query_matched or item[1] >= 6]

    best_score = ranked[0][1]
    selected = [canonical for canonical, score in ranked if score >= max(5, best_score - 1)]
    if best_score < 5:
        return ranked[:1] and [ranked[0][0]]
    return selected[:2]


def _contains_alias(text: str, alias: str) -> bool:
    escaped = re.escape(alias.lower())
    pattern = rf"(?<![a-z0-9]){escaped}(?:'s)?(?![a-z0-9])"
    return re.search(pattern, text) is not None


def _match_count(text: str, aliases: tuple[str, ...]) -> int:
    normalized = text.lower()
    return sum(1 for alias in aliases if _contains_alias(normalized, alias))


def _field_hit(text: str, aliases: tuple[str, ...]) -> bool:
    normalized = text.lower()
    return any(_contains_alias(normalized, alias) for alias in aliases)


def _lead_text(text: str, limit: int = 1200) -> str:
    compact = " ".join((text or "").split())
    return compact[:limit]


def _candidate_map(candidates: list[str] | None) -> dict[str, tuple[str, ...]]:
    candidate_map: dict[str, tuple[str, ...]] = {}
    source = candidates if candidates else list(COMPANY_ALIASES.keys())
    for candidate in source:
        cleaned = candidate.strip()
        if not cleaned:
            continue
        candidate_map[cleaned] = COMPANY_ALIASES.get(cleaned, _candidate_aliases(cleaned))
    return candidate_map


def _candidate_aliases(name: str) -> tuple[str, ...]:
    lowered = name.strip().lower()
    compact = re.sub(r"[^a-z0-9]+", " ", lowered).strip()
    collapsed = compact.replace(" ", "")
    aliases = [lowered]
    if compact and compact != lowered:
        aliases.append(compact)
    if collapsed and collapsed not in aliases:
        aliases.append(collapsed)
    return tuple(aliases)


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))
