from types import SimpleNamespace

from src.schemas.supervisor_state_schema import ApprovalStatus
from src.supervisor.supervisor import CentralSupervisor, SupervisorRunArtifacts


def test_block_preserves_partial_artifacts_as_revision_required():
    supervisor = CentralSupervisor()
    state, _ = supervisor.planner.create_state(
        run_id="run-artifact",
        user_query="HBM4 scan",
        technology_axes=["HBM4"],
        seed_competitors=["Micron"],
    )
    artifacts = SupervisorRunArtifacts(
        state=state,
        search_result=SimpleNamespace(normalized_evidence=[], quality_report=None),
    )

    result = supervisor._block(
        state,
        ["trl_results_missing"],
        artifacts=artifacts,
        reentry_stages=["technology_maturity_analysis"],
    )

    assert result.search_result is artifacts.search_result
    assert result.approval is not None
    assert result.approval.status == ApprovalStatus.REVISION_REQUIRED
    assert result.approval.reentry_stages == ["technology_maturity_analysis"]


def test_block_without_artifacts_stays_blocked():
    supervisor = CentralSupervisor()
    state, _ = supervisor.planner.create_state(
        run_id="run-blocked",
        user_query="HBM4 scan",
        technology_axes=["HBM4"],
        seed_competitors=["Micron"],
    )

    result = supervisor._block(state, ["query_bundles_missing"])

    assert result.approval is not None
    assert result.approval.status == ApprovalStatus.BLOCKED
