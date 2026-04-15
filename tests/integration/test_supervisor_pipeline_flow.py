from pathlib import Path

from src.agents.analysis.report_generation_agent import ReportGenerationAgent
from src.supervisor.supervisor import CentralSupervisor


def test_supervisor_pipeline_flow_end_to_end(tmp_path: Path):
    supervisor = CentralSupervisor(report_agent=ReportGenerationAgent(output_dir=tmp_path / "reports"))
    artifacts = supervisor.run(
        run_id="run-supervisor",
        user_query="HBM4 and PIM strategic scan",
        technology_axes=["HBM4", "PIM"],
        seed_competitors=["SK hynix", "Micron"],
    )

    assert artifacts.search_result is not None
    assert artifacts.trl_results
    assert artifacts.threat_results
    assert artifacts.merged_results
    assert artifacts.priority_rows
    assert artifacts.report is not None
    assert Path(artifacts.report.output_path).exists()
    assert artifacts.approval is not None
    assert artifacts.state.report_ref == artifacts.report.report_id
    assert artifacts.state.stage_status["global_quality_gate"].value == "passed"
    assert artifacts.state.stage_status["targeted_retry_if_needed"].value == "skipped"
