"""Deterministic merge node for TRL and Threat outputs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from ..schemas.analysis_output_schema import (
    ConfidenceLevel,
    MergedAnalysisResult,
    PriorityBucket,
    PriorityMatrixRow,
    ThreatAnalysisResult,
    ThreatLevel,
    TRLAnalysisResult,
    combine_confidence,
    confidence_rank,
)


class AnalysisMergeError(ValueError):
    pass


def _key(result: object) -> tuple[str, str, str]:
    return result.run_id, result.technology, result.company  # type: ignore[attr-defined]


def _trl_score(result: TRLAnalysisResult) -> int:
    if result.trl_score_high is not None:
        return result.trl_score_high
    if result.trl_score_low is not None:
        return result.trl_score_low
    return 0


def _priority_bucket(trl_result: TRLAnalysisResult, threat_result: ThreatAnalysisResult, conflict_flag: bool) -> tuple[PriorityBucket, str]:
    trl_score = _trl_score(trl_result)
    overlap = threat_result.strategic_overlap_score
    execution = threat_result.execution_credibility_score
    if conflict_flag or trl_result.unresolved or threat_result.unresolved:
        return PriorityBucket.REVIEW_REQUIRED, "Resolve unresolved or conflicting analysis before report generation."
    if threat_result.threat_level == ThreatLevel.HIGH and trl_score >= 7 and overlap >= 4:
        return PriorityBucket.IMMEDIATE_PRIORITY, "Act immediately on high-TRL, high-threat, high-overlap exposure."
    if threat_result.threat_level == ThreatLevel.HIGH and overlap >= 3 and trl_score >= 4:
        return PriorityBucket.STRATEGIC_WATCH, "Monitor strategically because threat is material and overlap is meaningful."
    if threat_result.threat_level == ThreatLevel.HIGH and execution >= 4:
        return PriorityBucket.EMERGING_RISK, "Track emerging execution risk even if TRL remains limited."
    if threat_result.threat_level == ThreatLevel.MEDIUM and overlap >= 4:
        return PriorityBucket.STRATEGIC_WATCH, "Maintain strategic watch on the overlap-heavy cell."
    return PriorityBucket.MONITOR, "Continue passive monitoring."


def _merged_confidence(trl_result: TRLAnalysisResult, threat_result: ThreatAnalysisResult, conflict_flag: bool) -> ConfidenceLevel:
    confidence = combine_confidence(trl_result.confidence, threat_result.confidence)
    if conflict_flag:
        return ConfidenceLevel.LOW
    if trl_result.unresolved or threat_result.unresolved:
        return ConfidenceLevel.LOW
    return confidence


def merge_analysis_results(
    trl_results: Iterable[TRLAnalysisResult],
    threat_results: Iterable[ThreatAnalysisResult],
) -> tuple[list[MergedAnalysisResult], list[PriorityMatrixRow]]:
    trl_map = {_key(result): result for result in trl_results}
    threat_map = {_key(result): result for result in threat_results}
    trl_keys = set(trl_map)
    threat_keys = set(threat_map)
    if trl_keys != threat_keys:
        missing_trl = sorted(threat_keys - trl_keys)
        missing_threat = sorted(trl_keys - threat_keys)
        raise AnalysisMergeError(
            f"analysis key mismatch: missing_trl={missing_trl} missing_threat={missing_threat}"
        )

    merged_results: list[MergedAnalysisResult] = []
    priority_rows: list[PriorityMatrixRow] = []
    for key in sorted(trl_keys):
        trl_result = trl_map[key]
        threat_result = threat_map[key]
        conflict_flag = bool(trl_result.unresolved or threat_result.has_conflict or threat_result.unresolved)
        priority_bucket, action_hint = _priority_bucket(trl_result, threat_result, conflict_flag)
        merged_confidence = _merged_confidence(trl_result, threat_result, conflict_flag)
        merged = MergedAnalysisResult(
            run_id=trl_result.run_id,
            technology=trl_result.technology,
            company=trl_result.company,
            trl_range=trl_result.trl_range,
            threat_level=threat_result.threat_level,
            merged_confidence=merged_confidence,
            conflict_flag=conflict_flag,
            priority_bucket=priority_bucket,
            action_hint=action_hint,
            unresolved=trl_result.unresolved or threat_result.unresolved,
            trl_reference_id=trl_result.evidence_ids[0] if trl_result.evidence_ids else None,
            threat_reference_id=threat_result.evidence_ids[0] if threat_result.evidence_ids else None,
            conflict_reference_id=threat_result.threat_reference_id if threat_result.has_conflict else None,
            notes=list(trl_result.notes) + list(threat_result.notes),
        )
        merged_results.append(merged)
        priority_rows.append(
            PriorityMatrixRow(
                run_id=merged.run_id,
                technology=merged.technology,
                company=merged.company,
                trl_range=merged.trl_range,
                threat_level=merged.threat_level,
                merged_confidence=merged.merged_confidence,
                conflict_flag=merged.conflict_flag,
                priority_bucket=merged.priority_bucket,
                action_hint=merged.action_hint,
                trl_reference_id=merged.trl_reference_id,
                threat_reference_id=merged.threat_reference_id,
                unresolved=merged.unresolved,
            )
        )
    return merged_results, priority_rows

