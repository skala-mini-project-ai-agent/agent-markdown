from src.schemas.report_output_schema import ReportFormat, ReportOutput, ReportSection, ReportStatus
from src.supervisor.stage_gate import StageGate


class DummyQuality:
    def __init__(self, analysis_ready: bool):
        self.analysis_ready = analysis_ready


def test_stage_gate_blocks_analysis_without_quality_report():
    gate = StageGate()
    decision = gate.check_analysis_ready(quality_report=None, evidence_items=[object()], allow_unresolved=True)
    assert decision.status.value == "blocked"


def test_stage_gate_allows_retry_when_unresolved_allowed():
    gate = StageGate()
    decision = gate.check_analysis_ready(
        quality_report=DummyQuality(False),
        evidence_items=[object()],
        allow_unresolved=True,
    )
    assert decision.status.value == "retry"


def test_stage_gate_final_approval_checks_required_sections():
    gate = StageGate()
    report = ReportOutput(
        report_id="rep1",
        run_id="r1",
        format=ReportFormat.MARKDOWN,
        status=ReportStatus.READY,
        sections=[ReportSection(section_id="summary", title="SUMMARY", body="x")],
        reference_trace=[],
        warnings=[],
        output_path="/tmp/report.md",
    )
    decision = gate.check_final_approval_ready(report)
    assert decision.status.value == "failed"


def test_stage_gate_blocks_on_blocking_warning_code():
    gate = StageGate()
    report = ReportOutput(
        report_id="rep2",
        run_id="r2",
        format=ReportFormat.MARKDOWN,
        status=ReportStatus.WARNING,
        sections=[
            ReportSection(section_id="summary", title="SUMMARY", body="x"),
            ReportSection(section_id="background", title="분석 배경", body="x"),
            ReportSection(section_id="technology_status", title="기술 현황", body="x"),
            ReportSection(section_id="competitor_trends", title="경쟁사 동향", body="x"),
            ReportSection(section_id="strategic_implications", title="전략적 시사점", body="x"),
            ReportSection(section_id="reference", title="REFERENCE", body="x"),
        ],
        reference_trace=[object()],
        warnings=[type("Warning", (), {"code": "UNRESOLVED_CELL"})()],
        output_path="/tmp/report.md",
    )
    decision = gate.check_final_approval_ready(report)
    assert decision.status.value == "failed"
