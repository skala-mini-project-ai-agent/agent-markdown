"""Canonical analysis output schema for TRL, Threat, merge, and priority matrix."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ThreatLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ThreatTier(str, Enum):
    TIER_1 = "tier_1"
    TIER_2 = "tier_2"
    TIER_3 = "tier_3"


class PriorityBucket(str, Enum):
    IMMEDIATE_PRIORITY = "immediate_priority"
    STRATEGIC_WATCH = "strategic_watch"
    EMERGING_RISK = "emerging_risk"
    MONITOR = "monitor"
    REVIEW_REQUIRED = "review_required"


@dataclass(slots=True)
class TRLAnalysisResult:
    run_id: str
    technology: str
    company: str
    trl_range: str
    trl_score_low: int | None
    trl_score_high: int | None
    confidence: ConfidenceLevel
    rationale: str
    direct_evidence_ids: list[str] = field(default_factory=list)
    indirect_evidence_ids: list[str] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)
    unresolved: bool = False
    quality_passed: bool = True
    signal_summary: dict[str, int] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def key(self) -> tuple[str, str, str]:
        return self.run_id, self.technology, self.company

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TRLAnalysisResult":
        return cls(
            run_id=data["run_id"],
            technology=data["technology"],
            company=data["company"],
            trl_range=data["trl_range"],
            trl_score_low=data.get("trl_score_low"),
            trl_score_high=data.get("trl_score_high"),
            confidence=ConfidenceLevel(data["confidence"]),
            rationale=data["rationale"],
            direct_evidence_ids=list(data.get("direct_evidence_ids", [])),
            indirect_evidence_ids=list(data.get("indirect_evidence_ids", [])),
            evidence_ids=list(data.get("evidence_ids", [])),
            unresolved=bool(data.get("unresolved", False)),
            quality_passed=bool(data.get("quality_passed", True)),
            signal_summary=dict(data.get("signal_summary", {})),
            notes=list(data.get("notes", [])),
        )


@dataclass(slots=True)
class ThreatAnalysisResult:
    run_id: str
    technology: str
    company: str
    threat_level: ThreatLevel
    threat_tier: ThreatTier
    impact_score: int
    immediacy_score: int
    execution_credibility_score: int
    strategic_overlap_score: int
    confidence: ConfidenceLevel
    rationale: str
    assumptions: list[str] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)
    unresolved: bool = False
    has_conflict: bool = False
    conflict_type: str | None = None
    trl_reference_id: str | None = None
    threat_reference_id: str | None = None
    resolution_notes: list[str] = field(default_factory=list)
    confidence_adjustment: str = "none"
    signal_summary: dict[str, int] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def key(self) -> tuple[str, str, str]:
        return self.run_id, self.technology, self.company

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["threat_level"] = self.threat_level.value
        payload["threat_tier"] = self.threat_tier.value
        payload["confidence"] = self.confidence.value
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ThreatAnalysisResult":
        return cls(
            run_id=data["run_id"],
            technology=data["technology"],
            company=data["company"],
            threat_level=ThreatLevel(data["threat_level"]),
            threat_tier=ThreatTier(data["threat_tier"]),
            impact_score=int(data["impact_score"]),
            immediacy_score=int(data["immediacy_score"]),
            execution_credibility_score=int(data["execution_credibility_score"]),
            strategic_overlap_score=int(data["strategic_overlap_score"]),
            confidence=ConfidenceLevel(data["confidence"]),
            rationale=data["rationale"],
            assumptions=list(data.get("assumptions", [])),
            evidence_ids=list(data.get("evidence_ids", [])),
            unresolved=bool(data.get("unresolved", False)),
            has_conflict=bool(data.get("has_conflict", False)),
            conflict_type=data.get("conflict_type"),
            trl_reference_id=data.get("trl_reference_id"),
            threat_reference_id=data.get("threat_reference_id"),
            resolution_notes=list(data.get("resolution_notes", [])),
            confidence_adjustment=data.get("confidence_adjustment", "none"),
            signal_summary=dict(data.get("signal_summary", {})),
            notes=list(data.get("notes", [])),
        )


@dataclass(slots=True)
class ConflictResolutionResult:
    run_id: str
    technology: str
    company: str
    has_conflict: bool
    conflict_type: str | None
    trl_reference_id: str | None
    threat_reference_id: str | None
    resolution_notes: list[str] = field(default_factory=list)
    confidence_adjustment: str = "none"
    unresolved: bool = False

    def key(self) -> tuple[str, str, str]:
        return self.run_id, self.technology, self.company

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConflictResolutionResult":
        return cls(
            run_id=data["run_id"],
            technology=data["technology"],
            company=data["company"],
            has_conflict=bool(data.get("has_conflict", False)),
            conflict_type=data.get("conflict_type"),
            trl_reference_id=data.get("trl_reference_id"),
            threat_reference_id=data.get("threat_reference_id"),
            resolution_notes=list(data.get("resolution_notes", [])),
            confidence_adjustment=data.get("confidence_adjustment", "none"),
            unresolved=bool(data.get("unresolved", False)),
        )


@dataclass(slots=True)
class PriorityMatrixRow:
    run_id: str
    technology: str
    company: str
    trl_range: str
    threat_level: ThreatLevel
    merged_confidence: ConfidenceLevel
    conflict_flag: bool
    priority_bucket: PriorityBucket
    action_hint: str
    trl_reference_id: str | None = None
    threat_reference_id: str | None = None
    unresolved: bool = False

    def key(self) -> tuple[str, str, str]:
        return self.run_id, self.technology, self.company

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["threat_level"] = self.threat_level.value
        payload["merged_confidence"] = self.merged_confidence.value
        payload["priority_bucket"] = self.priority_bucket.value
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PriorityMatrixRow":
        return cls(
            run_id=data["run_id"],
            technology=data["technology"],
            company=data["company"],
            trl_range=data["trl_range"],
            threat_level=ThreatLevel(data["threat_level"]),
            merged_confidence=ConfidenceLevel(data["merged_confidence"]),
            conflict_flag=bool(data["conflict_flag"]),
            priority_bucket=PriorityBucket(data["priority_bucket"]),
            action_hint=data["action_hint"],
            trl_reference_id=data.get("trl_reference_id"),
            threat_reference_id=data.get("threat_reference_id"),
            unresolved=bool(data.get("unresolved", False)),
        )


@dataclass(slots=True)
class MergedAnalysisResult:
    run_id: str
    technology: str
    company: str
    trl_range: str
    threat_level: ThreatLevel
    merged_confidence: ConfidenceLevel
    conflict_flag: bool
    priority_bucket: PriorityBucket
    action_hint: str
    unresolved: bool = False
    trl_reference_id: str | None = None
    threat_reference_id: str | None = None
    conflict_reference_id: str | None = None
    notes: list[str] = field(default_factory=list)

    def key(self) -> tuple[str, str, str]:
        return self.run_id, self.technology, self.company

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["threat_level"] = self.threat_level.value
        payload["merged_confidence"] = self.merged_confidence.value
        payload["priority_bucket"] = self.priority_bucket.value
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MergedAnalysisResult":
        return cls(
            run_id=data["run_id"],
            technology=data["technology"],
            company=data["company"],
            trl_range=data["trl_range"],
            threat_level=ThreatLevel(data["threat_level"]),
            merged_confidence=ConfidenceLevel(data["merged_confidence"]),
            conflict_flag=bool(data["conflict_flag"]),
            priority_bucket=PriorityBucket(data["priority_bucket"]),
            action_hint=data["action_hint"],
            unresolved=bool(data.get("unresolved", False)),
            trl_reference_id=data.get("trl_reference_id"),
            threat_reference_id=data.get("threat_reference_id"),
            conflict_reference_id=data.get("conflict_reference_id"),
            notes=list(data.get("notes", [])),
        )


def confidence_rank(confidence: ConfidenceLevel) -> int:
    return {
        ConfidenceLevel.HIGH: 3,
        ConfidenceLevel.MEDIUM: 2,
        ConfidenceLevel.LOW: 1,
    }[ConfidenceLevel(confidence)]


def combine_confidence(*values: ConfidenceLevel) -> ConfidenceLevel:
    if not values:
        return ConfidenceLevel.LOW
    rank = min(confidence_rank(ConfidenceLevel(value)) for value in values)
    return {
        3: ConfidenceLevel.HIGH,
        2: ConfidenceLevel.MEDIUM,
        1: ConfidenceLevel.LOW,
    }[rank]


def result_key(result: Any) -> tuple[str, str, str]:
    return result.run_id, result.technology, result.company

