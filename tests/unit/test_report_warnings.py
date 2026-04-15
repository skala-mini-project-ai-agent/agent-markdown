"""Unit tests for warning detection in ReportGenerationAgent."""

from __future__ import annotations

from pathlib import Path

from src.agents.analysis.report_generation_agent import ReportGenerationAgent
from src.schemas.analysis_output_schema import (
    ConfidenceLevel,
    MergedAnalysisResult,
    PriorityBucket,
    PriorityMatrixRow,
    ThreatLevel,
)


def _merged(
    technology: str = "PIM",
    company: str = "CorpC",
    trl_range: str = "5-6",
    threat_level: ThreatLevel = ThreatLevel.MEDIUM,
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM,
    conflict_flag: bool = False,
    unresolved: bool = False,
    priority_bucket: PriorityBucket = PriorityBucket.MONITOR,
) -> MergedAnalysisResult:
    return MergedAnalysisResult(
        run_id="run-warn",
        technology=technology,
        company=company,
        trl_range=trl_range,
        threat_level=threat_level,
        merged_confidence=confidence,
        conflict_flag=conflict_flag,
        priority_bucket=priority_bucket,
        action_hint="Monitor.",
        unresolved=unresolved,
    )


def _row(m: MergedAnalysisResult) -> PriorityMatrixRow:
    return PriorityMatrixRow(
        run_id=m.run_id,
        technology=m.technology,
        company=m.company,
        trl_range=m.trl_range,
        threat_level=m.threat_level,
        merged_confidence=m.merged_confidence,
        conflict_flag=m.conflict_flag,
        priority_bucket=m.priority_bucket,
        action_hint=m.action_hint,
        unresolved=m.unresolved,
    )


def test_no_warnings_for_clean_result(tmp_path: Path):
    agent = ReportGenerationAgent(output_dir=tmp_path)
    # trl_range="5-6" → high=6, MEDIUM numeric=5 → |6-5|=1 < threshold(3) → no divergence warning
    m = _merged(
        trl_range="5-6",
        threat_level=ThreatLevel.MEDIUM,
        confidence=ConfidenceLevel.HIGH,
    )
    report = agent.generate(run_id="run-warn", merged_results=[m], priority_matrix=[_row(m)])
    assert len(report.warnings) == 0


def test_unresolved_cell_warning(tmp_path: Path):
    agent = ReportGenerationAgent(output_dir=tmp_path)
    m = _merged(unresolved=True, priority_bucket=PriorityBucket.REVIEW_REQUIRED)
    report = agent.generate(run_id="run-warn", merged_results=[m], priority_matrix=[_row(m)])
    codes = {w.code for w in report.warnings}
    assert "UNRESOLVED_CELL" in codes
    w = next(w for w in report.warnings if w.code == "UNRESOLVED_CELL")
    assert "PIM/CorpC" in w.affected_cells


def test_conflict_flag_warning(tmp_path: Path):
    agent = ReportGenerationAgent(output_dir=tmp_path)
    m = _merged(conflict_flag=True, priority_bucket=PriorityBucket.REVIEW_REQUIRED)
    report = agent.generate(run_id="run-warn", merged_results=[m], priority_matrix=[_row(m)])
    codes = {w.code for w in report.warnings}
    assert "CONFLICT_FLAG" in codes


def test_low_confidence_warning(tmp_path: Path):
    agent = ReportGenerationAgent(output_dir=tmp_path)
    m = _merged(confidence=ConfidenceLevel.LOW)
    report = agent.generate(run_id="run-warn", merged_results=[m], priority_matrix=[_row(m)])
    codes = {w.code for w in report.warnings}
    assert "LOW_CONFIDENCE" in codes


def test_trl_threat_divergence_warning_high_trl_low_threat(tmp_path: Path):
    """TRL high=9 vs LOW threat(2) → |9-2|=7 → divergence."""
    agent = ReportGenerationAgent(output_dir=tmp_path)
    m = _merged(trl_range="8-9", threat_level=ThreatLevel.LOW, priority_bucket=PriorityBucket.MONITOR)
    report = agent.generate(run_id="run-warn", merged_results=[m], priority_matrix=[_row(m)])
    codes = {w.code for w in report.warnings}
    assert "TRL_THREAT_DIVERGENCE" in codes


def test_trl_threat_divergence_warning_low_trl_high_threat(tmp_path: Path):
    """TRL high=4 vs HIGH threat(8) → |4-8|=4 → divergence."""
    agent = ReportGenerationAgent(output_dir=tmp_path)
    m = _merged(trl_range="3-4", threat_level=ThreatLevel.HIGH, priority_bucket=PriorityBucket.EMERGING_RISK)
    report = agent.generate(run_id="run-warn", merged_results=[m], priority_matrix=[_row(m)])
    codes = {w.code for w in report.warnings}
    assert "TRL_THREAT_DIVERGENCE" in codes


def test_multiple_warnings_accumulated(tmp_path: Path):
    agent = ReportGenerationAgent(output_dir=tmp_path)
    m1 = _merged(company="CorpD", unresolved=True, priority_bucket=PriorityBucket.REVIEW_REQUIRED)
    m2 = _merged(company="CorpE", conflict_flag=True, priority_bucket=PriorityBucket.REVIEW_REQUIRED)
    report = agent.generate(
        run_id="run-warn",
        merged_results=[m1, m2],
        priority_matrix=[_row(m1), _row(m2)],
    )
    codes = {w.code for w in report.warnings}
    assert "UNRESOLVED_CELL" in codes
    assert "CONFLICT_FLAG" in codes
