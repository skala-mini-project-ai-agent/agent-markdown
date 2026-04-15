"""Schemas for supervisor state, retry plans, and approval decisions."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class StageStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"
    RETRY = "retry"


class ApprovalStatus(str, Enum):
    APPROVED = "approved"
    REVISION_REQUIRED = "revision_required"
    BLOCKED = "blocked"
    PENDING = "pending"


@dataclass(slots=True)
class RetryTarget:
    agent: str
    technology: str
    company: str
    reason: str
    source_type: str | None = None
    expansion_terms: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RetryPlan:
    run_id: str
    retry_targets: list[RetryTarget] = field(default_factory=list)
    retry_allowed: bool = True
    retry_count: int = 0
    unresolved_allowed: bool = False

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["retry_targets"] = [target.to_dict() for target in self.retry_targets]
        return payload


@dataclass(slots=True)
class ApprovalDecision:
    run_id: str
    status: ApprovalStatus
    reasons: list[str] = field(default_factory=list)
    reentry_stages: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["status"] = self.status.value
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ApprovalDecision":
        return cls(
            run_id=data["run_id"],
            status=ApprovalStatus(data["status"]),
            reasons=list(data.get("reasons", [])),
            reentry_stages=list(data.get("reentry_stages", [])),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(slots=True)
class SupervisorState:
    run_id: str
    user_query: str
    analysis_scope: str
    technology_axes: list[str] = field(default_factory=list)
    mode: str = "open_exploration_mode"
    query_bundles: dict[str, list[str]] = field(default_factory=dict)
    stage_status: dict[str, StageStatus] = field(default_factory=dict)
    retry_counts: dict[str, int] = field(default_factory=dict)
    quality_report_ref: str | None = None
    analysis_result_refs: dict[str, str] = field(default_factory=dict)
    report_ref: str | None = None
    approval_status: ApprovalStatus = ApprovalStatus.PENDING
    needs_review: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["stage_status"] = {key: value.value for key, value in self.stage_status.items()}
        payload["approval_status"] = self.approval_status.value
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SupervisorState":
        return cls(
            run_id=data["run_id"],
            user_query=data["user_query"],
            analysis_scope=data.get("analysis_scope", ""),
            technology_axes=list(data.get("technology_axes", [])),
            mode=data.get("mode", "open_exploration_mode"),
            query_bundles={key: list(value) for key, value in data.get("query_bundles", {}).items()},
            stage_status={
                key: StageStatus(value) for key, value in dict(data.get("stage_status", {})).items()
            },
            retry_counts={key: int(value) for key, value in dict(data.get("retry_counts", {})).items()},
            quality_report_ref=data.get("quality_report_ref"),
            analysis_result_refs=dict(data.get("analysis_result_refs", {})),
            report_ref=data.get("report_ref"),
            approval_status=ApprovalStatus(data.get("approval_status", ApprovalStatus.PENDING.value)),
            needs_review=bool(data.get("needs_review", False)),
            metadata=dict(data.get("metadata", {})),
        )
