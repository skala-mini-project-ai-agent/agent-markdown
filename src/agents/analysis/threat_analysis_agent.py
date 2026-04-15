"""Rule-based threat analysis agent."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable

from ...config.strategic_overlap import get_strategic_overlap_profile
from ...providers.llm.base_llm_provider import BaseLLMProvider
from ...schemas.analysis_output_schema import (
    ConfidenceLevel,
    ThreatAnalysisResult,
    ThreatLevel,
    ThreatTier,
)


def _norm(text: str) -> str:
    return " ".join(text.lower().replace("·", " ").replace("-", " ").split())


def _get_value(item: Any, field: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(field, default)
    return getattr(item, field, default)


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    if isinstance(value, tuple):
        return [str(v) for v in value]
    return [str(value)]


def _matches_company(candidate: Any, company: str) -> bool:
    if not company:
        return True
    normalized = _norm(company)
    values = _as_list(candidate)
    if not values:
        return True
    return any(normalized in _norm(value) or _norm(value) in normalized for value in values)


def _matches_technology(candidate: Any, technology: str) -> bool:
    normalized = _norm(technology)
    candidate_text = _norm(str(candidate or ""))
    return not technology or normalized in candidate_text or candidate_text in normalized


def _published_year(item: Any) -> int | None:
    raw = _get_value(item, "published_at")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).year
    except ValueError:
        return None


def _collect_text(item: Any) -> str:
    parts: list[str] = []
    for field in ("title", "raw_content", "source_name", "technology"):
        value = _get_value(item, field)
        if value:
            parts.append(str(value))
    for field in ("key_points", "signals", "counter_signals"):
        value = _get_value(item, field, [])
        if isinstance(value, list):
            parts.extend(str(v) for v in value)
        elif value:
            parts.append(str(value))
    return _norm(" ".join(parts))


_IMPACT_KEYWORDS = {
    5: ("mass production", "deployment", "qualification", "supply", "customer adoption"),
    4: ("pilot", "ramp", "design win", "commercialization"),
    3: ("prototype", "sample", "evaluation"),
    2: ("paper", "conference", "patent"),
}

_IMMEDIACY_KEYWORDS = {
    5: ("this year", "now", "current", "launch", "shipping", "mass production"),
    4: ("next year", "next 12 months", "ramp", "pilot"),
    3: ("roadmap", "planned", "future"),
    2: ("research", "study", "concept"),
}

_CREDIBILITY_KEYWORDS = {
    5: ("qualification", "deployment", "customer", "volume shipment", "mass production"),
    4: ("pilot", "engineering sample", "prototype validation"),
    3: ("conference", "paper", "patent", "job posting"),
    2: ("rumor", "commentary", "blog"),
}

_PUBLICITY_KEYWORDS = ("announcement", "press release", "media", "interview", "blog")


@dataclass(slots=True)
class ThreatBreakdown:
    impact_score: int
    immediacy_score: int
    execution_credibility_score: int
    strategic_overlap_score: int


class ThreatAnalysisAgent:
    def __init__(self, llm_provider: BaseLLMProvider | None = None):
        self.llm_provider = llm_provider

    def analyze(
        self,
        *,
        run_id: str,
        technology: str,
        company: str,
        evidence_items: Iterable[Any],
        trl_result: Any | None = None,
    ) -> ThreatAnalysisResult:
        matched_any: list[Any] = []
        relevant: list[Any] = []
        evidence_ids: list[str] = []
        texts: list[str] = []
        source_types: list[str] = []
        source_names: set[str] = set()
        direct_count = 0
        indirect_count = 0
        counter_count = 0
        recent_count = 0

        for item in evidence_items:
            if not _matches_technology(_get_value(item, "technology"), technology):
                continue
            if not _matches_company(_get_value(item, "company", []), company):
                continue
            matched_any.append(item)
            if not _get_value(item, "quality_passed", True):
                continue
            relevant.append(item)
            evidence_id = str(_get_value(item, "evidence_id") or _get_value(item, "id") or len(evidence_ids))
            evidence_ids.append(evidence_id)
            text = _collect_text(item)
            texts.append(text)
            source_types.append(str(_get_value(item, "source_type", "other")).lower())
            source_name = str(_get_value(item, "source_name", "")).strip()
            if source_name:
                source_names.add(source_name.lower())
            signal_type = str(_get_value(item, "signal_type", "direct")).lower()
            if signal_type == "direct":
                direct_count += 1
            elif signal_type == "indirect":
                indirect_count += 1
            else:
                counter_count += 1
            if (_published_year(item) or 0) >= 2024:
                recent_count += 1

        profile = get_strategic_overlap_profile(technology, company)
        data_status = "ok"
        if not matched_any:
            data_status = "no_data"
        elif not relevant:
            data_status = "coverage_gap"
        impact_score = self._score_axis(texts, _IMPACT_KEYWORDS, profile.score)
        immediacy_score = self._score_axis(texts, _IMMEDIACY_KEYWORDS, 3)
        execution_credibility_score = self._score_execution_credibility(
            texts=texts,
            source_types=source_types,
            direct_count=direct_count,
            indirect_count=indirect_count,
            recent_count=recent_count,
        )
        strategic_overlap_score = profile.score
        threat_level, threat_tier = self._derive_threat_level(
            impact_score=impact_score,
            immediacy_score=immediacy_score,
            execution_credibility_score=execution_credibility_score,
            strategic_overlap_score=strategic_overlap_score,
        )
        conflict = self._detect_conflict(
            trl_result,
            threat_level,
            threat_tier,
            impact_score=impact_score,
            immediacy_score=immediacy_score,
            execution_credibility_score=execution_credibility_score,
            evidence_items=relevant,
            texts=texts,
        )
        confidence = self._derive_confidence(
            relevant_count=len(relevant),
            direct_count=direct_count,
            indirect_count=indirect_count,
            counter_count=counter_count,
            source_diversity=len(source_names),
            has_conflict=conflict[0],
            data_status=data_status,
        )
        rationale = self._build_rationale(
            impact_score,
            immediacy_score,
            execution_credibility_score,
            strategic_overlap_score,
            direct_count,
            indirect_count,
            counter_count,
            conflict,
        )
        if self.llm_provider is not None:
            rationale = f"{rationale} | judge={self.llm_provider.generate_text(rationale).text}"
        trl_evidence_ids = list(getattr(trl_result, "evidence_ids", [])) if trl_result is not None else []
        return ThreatAnalysisResult(
            run_id=run_id,
            technology=technology,
            company=company,
            threat_level=threat_level,
            threat_tier=threat_tier,
            impact_score=impact_score,
            immediacy_score=immediacy_score,
            execution_credibility_score=execution_credibility_score,
            strategic_overlap_score=strategic_overlap_score,
            confidence=confidence,
            rationale=rationale,
            assumptions=list(profile.assumptions),
            evidence_ids=evidence_ids,
            unresolved=bool(relevant) and confidence == ConfidenceLevel.LOW and not conflict[0],
            data_status=data_status,
            has_conflict=conflict[0],
            conflict_type=conflict[1],
            trl_reference_id=(
                getattr(trl_result, "trl_reference_id", None)
                or (trl_evidence_ids[0] if trl_evidence_ids else None)
            ),
            threat_reference_id=evidence_ids[0] if evidence_ids else None,
            resolution_notes=conflict[2],
            confidence_adjustment=conflict[3],
            signal_summary={
                "direct": direct_count,
                "indirect": indirect_count,
                "counter": counter_count,
                "recent": recent_count,
                "source_diversity": len(source_names),
            },
            notes=(conflict[2] if conflict[2] else []) + ([] if data_status == "ok" else [data_status]),
        )

    def _score_axis(self, texts: list[str], keyword_table: dict[int, tuple[str, ...]], base: int) -> int:
        text = " ".join(texts)
        score = base
        for candidate, keywords in keyword_table.items():
            if any(keyword in text for keyword in keywords):
                score = max(score, candidate)
        return max(1, min(5, score))

    def _score_execution_credibility(
        self,
        *,
        texts: list[str],
        source_types: list[str],
        direct_count: int,
        indirect_count: int,
        recent_count: int,
    ) -> int:
        text = " ".join(texts)
        score = 2
        if direct_count >= 2:
            score += 1
        if recent_count >= 1:
            score += 1
        if len(set(source_types)) >= 2:
            score += 1
        if any(keyword in text for keyword in ("qualification", "deployment", "shipping", "mass production")):
            score += 1
        if indirect_count and direct_count == 0:
            score -= 1
        return max(1, min(5, score))

    def _derive_threat_level(
        self,
        *,
        impact_score: int,
        immediacy_score: int,
        execution_credibility_score: int,
        strategic_overlap_score: int,
    ) -> tuple[ThreatLevel, ThreatTier]:
        weighted = (
            impact_score * 0.25
            + immediacy_score * 0.2
            + execution_credibility_score * 0.3
            + strategic_overlap_score * 0.25
        )
        if weighted >= 4.2:
            return ThreatLevel.HIGH, ThreatTier.TIER_1
        if weighted >= 3.0:
            return ThreatLevel.MEDIUM, ThreatTier.TIER_2
        return ThreatLevel.LOW, ThreatTier.TIER_3

    def _detect_conflict(
        self,
        trl_result: Any | None,
        threat_level: ThreatLevel,
        threat_tier: ThreatTier,
        *,
        impact_score: int,
        immediacy_score: int,
        execution_credibility_score: int,
        evidence_items: list[Any],
        texts: list[str],
    ) -> tuple[bool, str | None, list[str], str]:
        notes: list[str] = []
        if trl_result is None:
            return False, None, notes, "none"
        trl_low = getattr(trl_result, "trl_score_low", None)
        trl_high = getattr(trl_result, "trl_score_high", None)
        text = " ".join(texts)
        publicity_only = any(keyword in text for keyword in _PUBLICITY_KEYWORDS) and not any(
            keyword in text for keyword in ("deployment", "shipping", "qualification", "mass production")
        )
        low_trl = trl_low is not None and trl_low <= 3
        high_trl = trl_high is not None and trl_high >= 8
        strong_execution = execution_credibility_score >= 4 and immediacy_score >= 4
        strong_overlap = getattr(trl_result, "technology", None) is not None and impact_score >= 4

        if low_trl and threat_tier == ThreatTier.TIER_1 and strong_execution:
            notes.append("low_trl_high_threat")
            return True, "timeline_mismatch", notes, "low"
        if high_trl and threat_level == ThreatLevel.LOW and strong_overlap:
            notes.append("high_trl_low_threat")
            return True, "coverage_bias", notes, "low"
        if publicity_only and (threat_level == ThreatLevel.HIGH or (impact_score >= 3 and immediacy_score >= 3)):
            notes.append("publicity_bias")
            return True, "publicity_bias", notes, "low"
        if getattr(trl_result, "unresolved", False) and threat_level == ThreatLevel.HIGH:
            notes.append("trl_unresolved_high_threat")
            return True, "evidence_strength_mismatch", notes, "low"
        if getattr(trl_result, "confidence", None) == ConfidenceLevel.LOW and threat_tier == ThreatTier.TIER_1 and strong_execution:
            notes.append("low_confidence_high_threat")
            return True, "confidence_mismatch", notes, "low"
        return False, None, notes, "none"

    def _derive_confidence(
        self,
        *,
        relevant_count: int,
        direct_count: int,
        indirect_count: int,
        counter_count: int,
        source_diversity: int,
        has_conflict: bool,
        data_status: str,
    ) -> ConfidenceLevel:
        if data_status in {"no_data", "coverage_gap"}:
            return ConfidenceLevel.LOW
        if has_conflict:
            return ConfidenceLevel.LOW
        if relevant_count >= 3 and direct_count >= 2 and source_diversity >= 2 and counter_count == 0:
            return ConfidenceLevel.HIGH
        if relevant_count >= 2 and direct_count >= 1 and source_diversity >= 2 and counter_count <= 1:
            return ConfidenceLevel.MEDIUM
        if relevant_count >= 1 and direct_count >= 1 and counter_count == 0:
            return ConfidenceLevel.MEDIUM
        if indirect_count and direct_count == 0:
            return ConfidenceLevel.LOW
        return ConfidenceLevel.LOW

    def _build_rationale(
        self,
        impact_score: int,
        immediacy_score: int,
        execution_credibility_score: int,
        strategic_overlap_score: int,
        direct_count: int,
        indirect_count: int,
        counter_count: int,
        conflict: tuple[bool, str | None, list[str], str],
    ) -> str:
        parts = [
            f"impact={impact_score}",
            f"immediacy={immediacy_score}",
            f"execution_credibility={execution_credibility_score}",
            f"strategic_overlap={strategic_overlap_score}",
            f"signals(direct={direct_count},indirect={indirect_count},counter={counter_count})",
        ]
        if conflict[0]:
            parts.append(f"conflict={conflict[1]}")
        return "; ".join(parts)
