"""Rule-based TRL analysis agent."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable

from ...providers.llm.base_llm_provider import BaseLLMProvider
from ...schemas.analysis_output_schema import ConfidenceLevel, TRLAnalysisResult


_DIRECT_KEYWORDS = [
    (9, ("mass production", "volume shipment", "customer qualification complete", "full deployment")),
    (8, ("qualification", "qualified supplier", "shipping", "commercial deployment", "customer adoption")),
    (7, ("engineering sample", "prototype validation", "pilot", "ramp", "production sample")),
    (6, ("tape-out", "lab validation", "proof of concept", "verification", "demonstrated")),
    (5, ("prototype", "bench test", "lab demonstration", "trial")),
    (4, ("feasibility", "concept validation", "research result")),
]

_INDIRECT_KEYWORDS = [
    (6, ("patent", "patented", "job posting", "hiring", "conference", "paper")),
    (5, ("research program", "organize team", "org chart", "roadmap")),
    (4, ("investor", "funding", "partnership", "ecosystem")),
]

_COUNTER_KEYWORDS = [
    (7, ("delay", "canceled", "scrapped", "halted", "recalled")),
    (6, ("risk", "bottleneck", "yield issue", "quality issue")),
]


def _norm(text: str) -> str:
    return " ".join(text.lower().replace("·", " ").replace("-", " ").split())


def _extract_text(item: Any) -> str:
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
        match = re.search(r"(20\d{2})", str(raw))
        return int(match.group(1)) if match else None


def _score_from_keywords(text: str, keyword_table: list[tuple[int, tuple[str, ...]]]) -> int:
    for score, keywords in keyword_table:
        if any(keyword in text for keyword in keywords):
            return score
    return 0


@dataclass(slots=True)
class TRLBreakdown:
    direct_score: int
    indirect_score: int
    counter_score: int


class TRLAnalysisAgent:
    def __init__(self, llm_provider: BaseLLMProvider | None = None):
        self.llm_provider = llm_provider

    def analyze(
        self,
        *,
        run_id: str,
        technology: str,
        company: str,
        evidence_items: Iterable[Any],
        quality_report: Any | None = None,
    ) -> TRLAnalysisResult:
        relevant: list[Any] = []
        direct_ids: list[str] = []
        indirect_ids: list[str] = []
        evidence_ids: list[str] = []
        direct_scores: list[int] = []
        indirect_scores: list[int] = []
        counter_scores: list[int] = []

        for item in evidence_items:
            if not _get_value(item, "quality_passed", True):
                continue
            if not _matches_technology(_get_value(item, "technology"), technology):
                continue
            if not _matches_company(_get_value(item, "company", []), company):
                continue
            relevant.append(item)
            evidence_id = str(_get_value(item, "evidence_id") or _get_value(item, "id") or len(evidence_ids))
            evidence_ids.append(evidence_id)

            text = _extract_text(item)
            signal_type = str(_get_value(item, "signal_type", "direct")).lower()
            direct_score = _score_from_keywords(text, _DIRECT_KEYWORDS)
            indirect_score = _score_from_keywords(text, _INDIRECT_KEYWORDS)
            counter_score = _score_from_keywords(text, _COUNTER_KEYWORDS)

            if signal_type == "counter_evidence":
                counter_scores.append(max(counter_score, direct_score, indirect_score))
            elif signal_type == "indirect" or indirect_score > direct_score:
                indirect_scores.append(max(indirect_score, 0))
                indirect_ids.append(evidence_id)
            else:
                direct_scores.append(max(direct_score, 0))
                direct_ids.append(evidence_id)

            if counter_score:
                counter_scores.append(counter_score)

        result = self._summarize(
            run_id=run_id,
            technology=technology,
            company=company,
            direct_ids=direct_ids,
            indirect_ids=indirect_ids,
            evidence_ids=evidence_ids,
            direct_scores=direct_scores,
            indirect_scores=indirect_scores,
            counter_scores=counter_scores,
            quality_report=quality_report,
        )
        return result

    def _summarize(
        self,
        *,
        run_id: str,
        technology: str,
        company: str,
        direct_ids: list[str],
        indirect_ids: list[str],
        evidence_ids: list[str],
        direct_scores: list[int],
        indirect_scores: list[int],
        counter_scores: list[int],
        quality_report: Any | None,
    ) -> TRLAnalysisResult:
        best_direct = max(direct_scores, default=0)
        best_indirect = max(indirect_scores, default=0)
        counter_penalty = 1 if max(counter_scores, default=0) >= 6 else 0

        if best_direct == 0 and best_indirect == 0:
            return TRLAnalysisResult(
                run_id=run_id,
                technology=technology,
                company=company,
                trl_range="unresolved",
                trl_score_low=None,
                trl_score_high=None,
                confidence=ConfidenceLevel.LOW,
                rationale="No quality-passed evidence matched the technology/company cell.",
                direct_evidence_ids=[],
                indirect_evidence_ids=[],
                evidence_ids=[],
                unresolved=True,
                quality_passed=bool(getattr(quality_report, "analysis_ready", True)),
                signal_summary={"direct": 0, "indirect": 0, "counter": 0},
                notes=["evidence_missing"],
            )

        low, high, confidence, notes = self._infer_range(best_direct, best_indirect, counter_penalty, direct_ids, indirect_ids)
        if low is None or high is None:
            return TRLAnalysisResult(
                run_id=run_id,
                technology=technology,
                company=company,
                trl_range="unresolved",
                trl_score_low=None,
                trl_score_high=None,
                confidence=ConfidenceLevel.LOW,
                rationale="Evidence exists but is not strong enough to support a stable TRL estimate.",
                direct_evidence_ids=direct_ids,
                indirect_evidence_ids=indirect_ids,
                evidence_ids=evidence_ids,
                unresolved=True,
                quality_passed=bool(getattr(quality_report, "analysis_ready", True)),
                signal_summary={"direct": len(direct_ids), "indirect": len(indirect_ids), "counter": len(counter_scores)},
                notes=notes or ["insufficient_strength"],
            )

        rationale = self._build_rationale(best_direct, best_indirect, counter_penalty, direct_ids, indirect_ids)
        if self.llm_provider is not None:
            response = self.llm_provider.generate_text(rationale)
            rationale = f"{rationale} | judge={response.text}"
        return TRLAnalysisResult(
            run_id=run_id,
            technology=technology,
            company=company,
            trl_range=f"{low}-{high}" if low != high else str(low),
            trl_score_low=low,
            trl_score_high=high,
            confidence=confidence,
            rationale=rationale,
            direct_evidence_ids=direct_ids,
            indirect_evidence_ids=indirect_ids,
            evidence_ids=evidence_ids,
            unresolved=False,
            quality_passed=bool(getattr(quality_report, "analysis_ready", True)),
            signal_summary={"direct": len(direct_ids), "indirect": len(indirect_ids), "counter": len(counter_scores)},
            notes=notes,
        )

    def _infer_range(
        self,
        direct_score: int,
        indirect_score: int,
        counter_penalty: int,
        direct_ids: list[str],
        indirect_ids: list[str],
    ) -> tuple[int | None, int | None, ConfidenceLevel, list[str]]:
        notes: list[str] = []
        if direct_score >= 8:
            low, high, confidence = 8, 9, ConfidenceLevel.HIGH
            if len(direct_ids) == 1:
                high = 8
                notes.append("single_direct_confirmation")
            return max(1, low - counter_penalty), max(1, high - counter_penalty), confidence, notes
        if direct_score == 7:
            confidence = ConfidenceLevel.HIGH if len(direct_ids) >= 2 else ConfidenceLevel.MEDIUM
            return max(1, 7 - counter_penalty), max(1, 8 - counter_penalty), confidence, notes
        if direct_score == 6:
            confidence = ConfidenceLevel.MEDIUM if indirect_score else ConfidenceLevel.HIGH
            return max(1, 6 - counter_penalty), max(1, 7 - counter_penalty), confidence, notes
        if direct_score == 5:
            confidence = ConfidenceLevel.MEDIUM
            return max(1, 5 - counter_penalty), max(1, 6 - counter_penalty), confidence, notes
        if direct_score == 4:
            confidence = ConfidenceLevel.LOW
            return max(1, 4 - counter_penalty), max(1, 5 - counter_penalty), confidence, notes
        if indirect_score >= 6:
            notes.append("indirect_only")
            return 4, 6, ConfidenceLevel.LOW, notes
        if indirect_score == 5:
            notes.append("indirect_only")
            return 4, 5, ConfidenceLevel.LOW, notes
        if indirect_score == 4:
            notes.append("indirect_only")
            return 3, 5, ConfidenceLevel.LOW, notes
        return None, None, ConfidenceLevel.LOW, ["weak_signal"]

    def _build_rationale(
        self,
        direct_score: int,
        indirect_score: int,
        counter_penalty: int,
        direct_ids: list[str],
        indirect_ids: list[str],
    ) -> str:
        parts = [
            f"direct_score={direct_score}",
            f"indirect_score={indirect_score}",
            f"counter_penalty={counter_penalty}",
        ]
        if direct_ids:
            parts.append(f"direct_evidence={','.join(direct_ids)}")
        if indirect_ids:
            parts.append(f"indirect_evidence={','.join(indirect_ids)}")
        if counter_penalty:
            parts.append("counter_signal_present")
        return "; ".join(parts)

