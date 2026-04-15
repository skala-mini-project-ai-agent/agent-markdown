"""Supervisor planning helpers."""

from __future__ import annotations

from dataclasses import dataclass

from ..config.agent_queries import AGENT_QUERY_TERMS
from ..config.settings import SupervisorSettings
from ..orchestration.execution_context import SupervisorExecutionContext
from ..schemas.supervisor_state_schema import ApprovalStatus, StageStatus, SupervisorState


DEFAULT_STAGE_NAMES = (
    "input_normalization",
    "supervisor_planning",
    "parallel_search",
    "global_quality_gate",
    "targeted_retry_if_needed",
    "technology_maturity_analysis",
    "threat_analysis",
    "merge_node",
    "report_generation",
    "final_approval",
)


@dataclass(slots=True)
class PlanningModule:
    settings: SupervisorSettings

    def create_state(
        self,
        *,
        run_id: str,
        user_query: str,
        technology_axes: list[str] | None = None,
        seed_competitors: list[str] | None = None,
        metadata: dict[str, object] | None = None,
    ) -> tuple[SupervisorState, SupervisorExecutionContext]:
        axes = list(technology_axes or self.settings.default_technology_axes)
        competitors = list(seed_competitors or self.settings.default_seed_competitors)
        mode = "seed_competitor_mode" if seed_competitors else "open_exploration_mode"
        query_bundles = self._build_query_bundles(user_query=user_query, technology_axes=axes)
        stage_status = {stage: StageStatus.PENDING for stage in DEFAULT_STAGE_NAMES}
        state = SupervisorState(
            run_id=run_id,
            user_query=user_query,
            analysis_scope=user_query.strip() or "technology strategy analysis",
            technology_axes=axes,
            mode=mode,
            query_bundles=query_bundles,
            stage_status=stage_status,
            retry_counts={},
            approval_status=ApprovalStatus.PENDING,
            metadata={**self.settings.metadata_defaults, **(metadata or {})},
        )
        context = SupervisorExecutionContext(
            run_id=run_id,
            user_query=user_query,
            technology_axes=axes,
            seed_competitors=competitors,
            output_format=str(state.metadata.get("output_format", self.settings.default_output_format)),
            freshness_start_year=int(state.metadata.get("freshness_start_year", 2024)),
            open_exploration_mode=(mode == "open_exploration_mode"),
            metadata=dict(state.metadata),
        )
        state.stage_status["input_normalization"] = StageStatus.PASSED
        state.stage_status["supervisor_planning"] = StageStatus.PASSED
        return state, context

    def _build_query_bundles(self, *, user_query: str, technology_axes: list[str]) -> dict[str, list[str]]:
        bundles: dict[str, list[str]] = {}
        for agent, terms in AGENT_QUERY_TERMS.items():
            queries = []
            for term in terms:
                queries.append(f"{user_query} {term}".strip())
            bundles[agent] = queries
        if technology_axes:
            bundles["technology_axes"] = list(technology_axes)
        return bundles
