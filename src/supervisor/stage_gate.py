"""Rule-based stage gate checks for supervisor flow."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

from ..config.report_sections import SECTION_IDS
from ..config.settings import SupervisorSettings
from ..schemas.report_output_schema import ReportOutput
from ..schemas.supervisor_state_schema import StageStatus, SupervisorState


@dataclass(slots=True)
class GateDecision:
    status: StageStatus
    reasons: list[str] = field(default_factory=list)


class StageGate:
    def __init__(self, settings: SupervisorSettings | None = None) -> None:
        self.settings = settings or SupervisorSettings()

    def check_search_ready(self, state: SupervisorState) -> GateDecision:
        if not state.query_bundles:
            return GateDecision(StageStatus.BLOCKED, ["query_bundles_missing"])
        return GateDecision(StageStatus.PASSED)

    def check_analysis_ready(
        self,
        *,
        quality_report: Any | None,
        evidence_items: Sequence[Any],
        allow_unresolved: bool,
    ) -> GateDecision:
        if quality_report is None:
            return GateDecision(StageStatus.BLOCKED, ["quality_report_missing"])
        if not evidence_items:
            return GateDecision(StageStatus.BLOCKED, ["normalized_evidence_missing"])
        if getattr(quality_report, "analysis_ready", False):
            return GateDecision(StageStatus.PASSED)
        if allow_unresolved:
            return GateDecision(StageStatus.RETRY, ["analysis_ready_false_but_unresolved_allowed"])
        return GateDecision(StageStatus.BLOCKED, ["quality_gate_not_passed"])

    def check_merge_ready(self, *, trl_results: Sequence[Any], threat_results: Sequence[Any]) -> GateDecision:
        if not trl_results:
            return GateDecision(StageStatus.BLOCKED, ["trl_results_missing"])
        if not threat_results:
            return GateDecision(StageStatus.BLOCKED, ["threat_results_missing"])
        return GateDecision(StageStatus.PASSED)

    def check_report_ready(
        self,
        *,
        merged_results: Sequence[Any],
        priority_rows: Sequence[Any],
        evidence_items: Sequence[Any],
    ) -> GateDecision:
        reasons: list[str] = []
        if not merged_results:
            reasons.append("merged_results_missing")
        if not priority_rows:
            reasons.append("priority_matrix_missing")
        if not evidence_items:
            reasons.append("reference_trace_source_missing")
        if reasons:
            return GateDecision(StageStatus.BLOCKED, reasons)
        return GateDecision(StageStatus.PASSED)

    def check_final_approval_ready(self, report: ReportOutput | None) -> GateDecision:
        if report is None:
            return GateDecision(StageStatus.BLOCKED, ["report_missing"])
        section_ids = {section.section_id for section in report.sections}
        missing = [section_id for section_id in SECTION_IDS if section_id not in section_ids]
        if missing:
            return GateDecision(StageStatus.FAILED, [f"missing_sections:{','.join(missing)}"])
        if not report.reference_trace:
            return GateDecision(StageStatus.FAILED, ["reference_trace_missing"])
        if not report.output_path:
            return GateDecision(StageStatus.FAILED, ["output_path_missing"])
        blocking_codes = set(self.settings.final_approval_blocking_warning_codes)
        warning_codes = {warning.code for warning in report.warnings}
        blocking_hits = sorted(blocking_codes.intersection(warning_codes))
        if blocking_hits:
            return GateDecision(StageStatus.FAILED, [f"blocking_warnings:{','.join(blocking_hits)}"])
        if len(report.warnings) > self.settings.final_approval_max_warning_count:
            return GateDecision(StageStatus.FAILED, ["warning_count_exceeded"])
        return GateDecision(StageStatus.PASSED)
