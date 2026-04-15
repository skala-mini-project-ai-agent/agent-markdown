"""Central supervisor orchestration for the analysis pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..agents.analysis.report_generation_agent import ReportGenerationAgent
from ..agents.analysis.threat_analysis_agent import ThreatAnalysisAgent
from ..agents.analysis.trl_analysis_agent import TRLAnalysisAgent
from ..config.settings import SupervisorSettings
from ..orchestration.merge_node import merge_analysis_results
from ..orchestration.parallel_search_runner import ParallelSearchRunner
from ..orchestration.stage_executor import StageExecutor
from ..providers.embedding.base_embedding_provider import BaseEmbeddingProvider
from ..providers.embedding.noop_embedding_provider import NoopEmbeddingProvider
from ..schemas.report_output_schema import ReportFormat, ReportOutput, ReportStatus
from ..schemas.supervisor_state_schema import (
    ApprovalDecision,
    ApprovalStatus,
    StageStatus,
    SupervisorState,
)
from ..storage.repositories.analysis_result_repository import AnalysisResultRepository
from ..storage.repositories.execution_state_repository import ExecutionStateRepository
from ..storage.repositories.report_repository import ReportRepository
from .planning import PlanningModule
from .retry_controller import RetryController
from .stage_gate import StageGate


@dataclass(slots=True)
class SupervisorRunArtifacts:
    state: SupervisorState
    search_result: Any | None = None
    trl_results: list[Any] = field(default_factory=list)
    threat_results: list[Any] = field(default_factory=list)
    merged_results: list[Any] = field(default_factory=list)
    priority_rows: list[Any] = field(default_factory=list)
    report: ReportOutput | None = None
    approval: ApprovalDecision | None = None


class CentralSupervisor:
    def __init__(
        self,
        *,
        settings: SupervisorSettings | None = None,
        planner: PlanningModule | None = None,
        stage_gate: StageGate | None = None,
        retry_controller: RetryController | None = None,
        search_runner: ParallelSearchRunner | None = None,
        trl_agent: TRLAnalysisAgent | None = None,
        threat_agent: ThreatAnalysisAgent | None = None,
        report_agent: ReportGenerationAgent | None = None,
        embedding_provider: BaseEmbeddingProvider | None = None,
        stage_executor: StageExecutor | None = None,
        execution_state_repository: ExecutionStateRepository | None = None,
        analysis_result_repository: AnalysisResultRepository | None = None,
        report_repository: ReportRepository | None = None,
    ) -> None:
        self.settings = settings or SupervisorSettings()
        self.planner = planner or PlanningModule(self.settings)
        self.stage_gate = stage_gate or StageGate(self.settings)
        self.embedding_provider = embedding_provider or NoopEmbeddingProvider()
        self.retry_controller = retry_controller or RetryController(self.settings, embedding_provider=self.embedding_provider)
        self.search_runner = search_runner or ParallelSearchRunner(embedding_provider=self.embedding_provider)
        self.trl_agent = trl_agent or TRLAnalysisAgent()
        self.threat_agent = threat_agent or ThreatAnalysisAgent()
        self.report_agent = report_agent or ReportGenerationAgent(embedding_provider=self.embedding_provider)
        self.stage_executor = stage_executor or StageExecutor()
        self.execution_state_repository = execution_state_repository or ExecutionStateRepository()
        self.analysis_result_repository = analysis_result_repository or AnalysisResultRepository()
        self.report_repository = report_repository or ReportRepository()

    def run(
        self,
        *,
        run_id: str,
        user_query: str,
        technology_axes: list[str] | None = None,
        seed_competitors: list[str] | None = None,
        metadata: dict[str, object] | None = None,
    ) -> SupervisorRunArtifacts:
        state, context = self.planner.create_state(
            run_id=run_id,
            user_query=user_query,
            technology_axes=technology_axes,
            seed_competitors=seed_competitors,
            metadata=metadata,
        )
        self.execution_state_repository.save_state(state)
        artifacts = SupervisorRunArtifacts(state=state)

        search_gate = self.stage_gate.check_search_ready(state)
        if search_gate.status != StageStatus.PASSED:
            return self._block(state, search_gate.reasons)

        search_result = self._run_search_with_retry(state, context.to_search_context())
        artifacts.search_result = search_result
        if search_result is None:
            return self._block(state, ["search_result_missing_after_retry"], artifacts=artifacts)
        state.stage_status["parallel_search"] = StageStatus.PASSED
        state.stage_status["global_quality_gate"] = (
            StageStatus.PASSED if getattr(search_result.quality_report, "analysis_ready", False) else StageStatus.FAILED
        )
        state.quality_report_ref = state.run_id if search_result.quality_report is not None else None
        self.execution_state_repository.save_state(state)

        analysis_gate = self.stage_gate.check_analysis_ready(
            quality_report=search_result.quality_report,
            evidence_items=search_result.normalized_evidence,
            allow_unresolved=self.settings.allow_analysis_on_warning,
        )
        if analysis_gate.status == StageStatus.BLOCKED:
            return self._block(state, analysis_gate.reasons, artifacts=artifacts, reentry_stages=["parallel_search"])
        if analysis_gate.status == StageStatus.RETRY:
            retry_count = state.retry_counts.get("global_quality_gate", 0)
            if retry_count >= self.settings.max_retry_count and not self.settings.allow_unresolved_after_retry_limit:
                return self._block(
                    state,
                    ["retry_limit_exceeded"],
                    artifacts=artifacts,
                    reentry_stages=["parallel_search"],
                )
        else:
            state.stage_status["targeted_retry_if_needed"] = StageStatus.SKIPPED

        trl_results = self._run_trl_stage(state, search_result.normalized_evidence, search_result.quality_report)
        threat_results = self._run_threat_stage(state, search_result.normalized_evidence, trl_results)
        artifacts.trl_results = trl_results
        artifacts.threat_results = threat_results

        merge_gate = self.stage_gate.check_merge_ready(trl_results=trl_results, threat_results=threat_results)
        if merge_gate.status != StageStatus.PASSED:
            return self._block(
                state,
                merge_gate.reasons,
                artifacts=artifacts,
                reentry_stages=["parallel_search", "technology_maturity_analysis", "threat_analysis"],
            )

        merged_results, priority_rows = merge_analysis_results(trl_results, threat_results)
        state.stage_status["merge_node"] = StageStatus.PASSED
        self.execution_state_repository.save_state(state)
        artifacts.merged_results = merged_results
        artifacts.priority_rows = priority_rows
        for merged in merged_results:
            self.analysis_result_repository.store_merged_result(merged)
        self.analysis_result_repository.store_priority_rows(priority_rows)

        report_gate = self.stage_gate.check_report_ready(
            merged_results=merged_results,
            priority_rows=priority_rows,
            evidence_items=search_result.normalized_evidence,
        )
        if report_gate.status != StageStatus.PASSED:
            return self._block(
                state,
                report_gate.reasons,
                artifacts=artifacts,
                reentry_stages=["merge_node", "report_generation"],
            )

        report = self.report_agent.generate(
            run_id=run_id,
            merged_results=merged_results,
            priority_matrix=priority_rows,
            evidence_items=search_result.normalized_evidence,
            output_format=ReportFormat(self.settings.default_output_format),
        )
        self.report_repository.save(report)
        state.report_ref = report.report_id
        state.stage_status["report_generation"] = StageStatus.PASSED
        self.execution_state_repository.save_state(state)
        artifacts.report = report

        approval = self._final_approval(state, report)
        artifacts.approval = approval
        return artifacts

    def _run_search_with_retry(self, state: SupervisorState, search_context: Any) -> Any | None:
        latest_result = None
        attempt = 0
        previous_signature: tuple[Any, ...] | None = None
        previous_score: tuple[int, int, int, int] | None = None
        while True:
            attempt += 1
            state.stage_status["parallel_search"] = StageStatus.IN_PROGRESS
            self.execution_state_repository.save_state(state)
            latest_result = self.stage_executor.run_stage(
                "parallel_search",
                self.search_runner.run,
                search_context,
            ).payload
            quality_report = getattr(latest_result, "quality_report", None)
            if quality_report is not None and getattr(quality_report, "analysis_ready", False):
                state.stage_status["targeted_retry_if_needed"] = StageStatus.SKIPPED
                self.execution_state_repository.save_state(state)
                return latest_result

            current_signature = self._quality_signature(quality_report)
            current_score = self._quality_score(quality_report)

            current_retry_count = state.retry_counts.get("global_quality_gate", 0)
            plan = self.retry_controller.build_retry_plan(
                run_id=state.run_id,
                quality_report=quality_report,
                current_retry_count=current_retry_count,
                evidence_items=list(getattr(latest_result, "normalized_evidence", [])),
            )
            state.retry_counts["global_quality_gate"] = plan.retry_count
            state.stage_status["targeted_retry_if_needed"] = StageStatus.RETRY
            self.execution_state_repository.save_retry_plan(plan)
            self.execution_state_repository.save_state(state)

            if not self._should_continue_retry(
                current_signature=current_signature,
                current_score=current_score,
                previous_signature=previous_signature,
                previous_score=previous_score,
                plan=plan,
            ):
                state.stage_status["targeted_retry_if_needed"] = StageStatus.PASSED
                self.execution_state_repository.save_state(state)
                return latest_result

            if not plan.retry_allowed:
                state.stage_status["targeted_retry_if_needed"] = (
                    StageStatus.PASSED if plan.unresolved_allowed else StageStatus.FAILED
                )
                self.execution_state_repository.save_state(state)
                return latest_result if plan.unresolved_allowed else None

            previous_signature = current_signature
            previous_score = current_score
            search_context.metadata["retry_plan"] = plan.to_dict()
            search_context.metadata["retry_attempt"] = attempt

    def _quality_signature(self, quality_report: Any | None) -> tuple[Any, ...]:
        if quality_report is None:
            return ("missing",)
        low_evidence = sorted(
            (str(cell.get("technology", "")), str(cell.get("company", "")))
            for cell in list(getattr(quality_report, "low_evidence_cells", []))
        )
        low_confidence = sorted(
            (str(cell.get("technology", "")), str(cell.get("company", "")))
            for cell in list(getattr(quality_report, "low_confidence_cells", []))
        )
        conflicts = sorted(
            (
                str(flag.get("technology", "")),
                str(flag.get("company", "")),
                str(flag.get("reason", flag.get("type", ""))),
            )
            for flag in list(getattr(quality_report, "conflict_flags", []))
        )
        bias = sorted(
            (
                str(flag.get("type", "")),
                str(flag.get("company", "")),
                str(flag.get("source_type", "")),
            )
            for flag in list(getattr(quality_report, "bias_flags", []))
        )
        return (
            getattr(quality_report, "status", ""),
            tuple(low_evidence),
            tuple(low_confidence),
            tuple(conflicts),
            tuple(bias),
        )

    def _quality_score(self, quality_report: Any | None) -> tuple[int, int, int, int]:
        if quality_report is None:
            return (10**9, 10**9, 10**9, 10**9)
        return (
            len(list(getattr(quality_report, "low_evidence_cells", []))),
            len(list(getattr(quality_report, "low_confidence_cells", []))),
            len(list(getattr(quality_report, "conflict_flags", []))),
            len(list(getattr(quality_report, "bias_flags", []))),
        )

    def _should_continue_retry(
        self,
        *,
        current_signature: tuple[Any, ...],
        current_score: tuple[int, int, int, int],
        previous_signature: tuple[Any, ...] | None,
        previous_score: tuple[int, int, int, int] | None,
        plan: Any,
    ) -> bool:
        if not getattr(plan, "retry_allowed", False):
            return True
        if not getattr(plan, "retry_targets", []):
            return False
        if previous_signature is not None and current_signature == previous_signature:
            return False
        if previous_score is not None and current_score >= previous_score:
            return False
        return True

    def _run_trl_stage(self, state: SupervisorState, evidence_items: list[Any], quality_report: Any) -> list[Any]:
        state.stage_status["technology_maturity_analysis"] = StageStatus.IN_PROGRESS
        results = []
        for technology in sorted({item.technology for item in evidence_items}):
            companies = sorted({company for item in evidence_items if item.technology == technology for company in item.company})
            for company in companies:
                result = self.trl_agent.analyze(
                    run_id=state.run_id,
                    technology=technology,
                    company=company,
                    evidence_items=evidence_items,
                    quality_report=quality_report,
                )
                self.analysis_result_repository.store_trl_result(result)
                results.append(result)
        state.stage_status["technology_maturity_analysis"] = StageStatus.PASSED
        self.execution_state_repository.save_state(state)
        return results

    def _run_threat_stage(self, state: SupervisorState, evidence_items: list[Any], trl_results: list[Any]) -> list[Any]:
        state.stage_status["threat_analysis"] = StageStatus.IN_PROGRESS
        trl_map = {(result.technology, result.company): result for result in trl_results}
        results = []
        for technology, company in sorted(trl_map):
            result = self.threat_agent.analyze(
                run_id=state.run_id,
                technology=technology,
                company=company,
                evidence_items=evidence_items,
                trl_result=trl_map[(technology, company)],
            )
            self.analysis_result_repository.store_threat_result(result)
            results.append(result)
        state.stage_status["threat_analysis"] = StageStatus.PASSED
        self.execution_state_repository.save_state(state)
        return results

    def _final_approval(self, state: SupervisorState, report: ReportOutput) -> ApprovalDecision:
        gate = self.stage_gate.check_final_approval_ready(report)
        reasons = list(gate.reasons)
        reentry_stages: list[str] = []
        status = ApprovalStatus.APPROVED

        if gate.status in {StageStatus.BLOCKED, StageStatus.FAILED}:
            status = ApprovalStatus.REVISION_REQUIRED
            reentry_stages = ["report_generation"]
        elif report.status == ReportStatus.BLOCKED:
            status = ApprovalStatus.REVISION_REQUIRED
            reasons.append("report_status_requires_review")
            reentry_stages = ["report_generation"]
        elif report.status == ReportStatus.WARNING and not self.settings.final_approval_allow_warning_status:
            status = ApprovalStatus.REVISION_REQUIRED
            reasons.append("warning_status_not_allowed")
            reentry_stages = ["report_generation"]

        decision = ApprovalDecision(
            run_id=state.run_id,
            status=status,
            reasons=reasons,
            reentry_stages=reentry_stages,
            metadata={"report_ref": report.report_id},
        )
        state.stage_status["final_approval"] = StageStatus.PASSED if status == ApprovalStatus.APPROVED else StageStatus.FAILED
        state.approval_status = status
        state.needs_review = status != ApprovalStatus.APPROVED
        self.execution_state_repository.save_state(state)
        self.execution_state_repository.save_approval_decision(decision)
        return decision

    def _block(
        self,
        state: SupervisorState,
        reasons: list[str],
        *,
        artifacts: SupervisorRunArtifacts | None = None,
        reentry_stages: list[str] | None = None,
    ) -> SupervisorRunArtifacts:
        has_partial_artifacts = bool(
            artifacts
            and (
                artifacts.search_result is not None
                or artifacts.trl_results
                or artifacts.threat_results
                or artifacts.merged_results
                or artifacts.report is not None
            )
        )
        status = ApprovalStatus.REVISION_REQUIRED if has_partial_artifacts else ApprovalStatus.BLOCKED
        decision = ApprovalDecision(
            run_id=state.run_id,
            status=status,
            reasons=reasons,
            reentry_stages=list(reentry_stages or []),
            metadata={
                "has_search_result": bool(artifacts and artifacts.search_result is not None),
                "has_report": bool(artifacts and artifacts.report is not None),
            },
        )
        state.approval_status = status
        state.needs_review = True
        state.stage_status["final_approval"] = StageStatus.FAILED
        self.execution_state_repository.save_state(state)
        self.execution_state_repository.save_approval_decision(decision)
        if artifacts is None:
            return SupervisorRunArtifacts(state=state, approval=decision)
        artifacts.state = state
        artifacts.approval = decision
        return artifacts
