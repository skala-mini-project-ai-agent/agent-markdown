from pathlib import Path

from src.agents.analysis.report_generation_agent import ReportGenerationAgent
from src.schemas.analysis_output_schema import ConfidenceLevel, MergedAnalysisResult, PriorityBucket, PriorityMatrixRow, ThreatLevel
from src.schemas.normalized_evidence_schema import NormalizedEvidence
from src.supervisor.supervisor import CentralSupervisor


def _report(tmp_path: Path):
    agent = ReportGenerationAgent(output_dir=tmp_path)
    merged = MergedAnalysisResult(
        run_id="r1",
        technology="HBM4",
        company="Company A",
        trl_range="6-7",
        threat_level=ThreatLevel.HIGH,
        merged_confidence=ConfidenceLevel.MEDIUM,
        conflict_flag=False,
        priority_bucket=PriorityBucket.STRATEGIC_WATCH,
        action_hint="watch",
        trl_reference_id="ev1",
        threat_reference_id="ev1",
    )
    row = PriorityMatrixRow(
        run_id="r1",
        technology="HBM4",
        company="Company A",
        trl_range="6-7",
        threat_level=ThreatLevel.HIGH,
        merged_confidence=ConfidenceLevel.MEDIUM,
        conflict_flag=False,
        priority_bucket=PriorityBucket.STRATEGIC_WATCH,
        action_hint="watch",
        trl_reference_id="ev1",
        threat_reference_id="ev1",
    )
    ev = NormalizedEvidence(
        evidence_id="ev1",
        run_id="r1",
        agent_type="hbm4",
        technology="HBM4",
        company=["Company A"],
        title="evidence",
        source_type="paper",
        signal_type="direct",
        source_name="IEEE",
        published_at="2025-01-01T00:00:00Z",
        url="https://example.com",
        raw_content="content",
        key_points=["k"],
        signals=["s"],
        quality_passed=True,
    )
    return agent.generate(run_id="r1", merged_results=[merged], priority_matrix=[row], evidence_items=[ev])


def test_final_approval_marks_ready_report_approved(tmp_path: Path):
    supervisor = CentralSupervisor()
    state, _ = supervisor.planner.create_state(run_id="r1", user_query="HBM4 scan")
    report = _report(tmp_path)
    decision = supervisor._final_approval(state, report)

    assert decision.status.value == "approved"


def test_final_approval_allows_warning_when_non_blocking(tmp_path: Path):
    supervisor = CentralSupervisor()
    state, _ = supervisor.planner.create_state(run_id="r2", user_query="HBM4 scan")
    report = _report(tmp_path)
    report.status = report.status.WARNING
    report.warnings = []

    decision = supervisor._final_approval(state, report)

    assert decision.status.value == "approved"
