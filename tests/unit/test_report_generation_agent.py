"""Unit tests for ReportGenerationAgent."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from src.agents.analysis.report_generation_agent import ReportGenerationAgent
from src.config.report_sections import SECTION_IDS
from src.schemas.analysis_output_schema import (
    ConfidenceLevel,
    MergedAnalysisResult,
    PriorityBucket,
    PriorityMatrixRow,
    ThreatLevel,
)
from src.schemas.normalized_evidence_schema import NormalizedEvidence
from src.schemas.report_output_schema import ReportFormat, ReportStatus


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _merged(
    technology: str = "HBM4",
    company: str = "CompanyA",
    trl_range: str = "6-7",
    threat_level: ThreatLevel = ThreatLevel.HIGH,
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM,
    conflict_flag: bool = False,
    priority_bucket: PriorityBucket = PriorityBucket.STRATEGIC_WATCH,
    unresolved: bool = False,
    data_status: str = "ok",
    trl_ref: str | None = "ev-001",
    threat_ref: str | None = "ev-002",
) -> MergedAnalysisResult:
    return MergedAnalysisResult(
        run_id="run-test",
        technology=technology,
        company=company,
        trl_range=trl_range,
        threat_level=threat_level,
        merged_confidence=confidence,
        conflict_flag=conflict_flag,
        priority_bucket=priority_bucket,
        action_hint="Monitor strategically.",
        unresolved=unresolved,
        data_status=data_status,
        trl_reference_id=trl_ref,
        threat_reference_id=threat_ref,
    )


def _priority_row(merged: MergedAnalysisResult) -> PriorityMatrixRow:
    return PriorityMatrixRow(
        run_id=merged.run_id,
        technology=merged.technology,
        company=merged.company,
        trl_range=merged.trl_range,
        threat_level=merged.threat_level,
        merged_confidence=merged.merged_confidence,
        conflict_flag=merged.conflict_flag,
        priority_bucket=merged.priority_bucket,
        action_hint=merged.action_hint,
        trl_reference_id=merged.trl_reference_id,
        threat_reference_id=merged.threat_reference_id,
        unresolved=merged.unresolved,
        data_status=merged.data_status,
    )


def _evidence(evidence_id: str = "ev-001", raw_content: str = "Sample raw content.") -> NormalizedEvidence:
    return NormalizedEvidence(
        evidence_id=evidence_id,
        run_id="run-test",
        agent_type="hbm4",
        technology="HBM4",
        company=["CompanyA"],
        title="Sample Evidence Title",
        source_type="paper",
        signal_type="direct",
        source_name="IEEE",
        published_at="2025-01-01T00:00:00Z",
        url="https://example.com/paper",
        raw_content=raw_content,
        key_points=["key point 1"],
        signals=["signal 1"],
        quality_passed=True,
    )


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _make_agent(tmp_path: Path) -> ReportGenerationAgent:
    return ReportGenerationAgent(output_dir=tmp_path)


# ---------------------------------------------------------------------------
# Tests: required sections present
# ---------------------------------------------------------------------------

def test_all_required_sections_generated(tmp_path: Path):
    agent = _make_agent(tmp_path)
    m = _merged()
    report = agent.generate(
        run_id="run-test",
        merged_results=[m],
        priority_matrix=[_priority_row(m)],
        evidence_items=[_evidence("ev-001"), _evidence("ev-002", "Other content.")],
    )
    section_ids = {s.section_id for s in report.sections}
    for sid in SECTION_IDS:
        assert sid in section_ids, f"Missing required section: {sid}"


def test_section_order_is_deterministic(tmp_path: Path):
    agent = _make_agent(tmp_path)
    m = _merged()
    report1 = agent.generate(
        run_id="run-test",
        merged_results=[m],
        priority_matrix=[_priority_row(m)],
    )
    report2 = agent.generate(
        run_id="run-test",
        merged_results=[m],
        priority_matrix=[_priority_row(m)],
    )
    ids1 = [s.section_id for s in report1.sections]
    ids2 = [s.section_id for s in report2.sections]
    assert ids1 == ids2


def test_summary_section_contains_executive_overview(tmp_path: Path):
    agent = _make_agent(tmp_path)
    m1 = _merged(company="CompanyA", priority_bucket=PriorityBucket.IMMEDIATE_PRIORITY)
    m2 = _merged(
        technology="PIM",
        company="CompanyB",
        priority_bucket=PriorityBucket.STRATEGIC_WATCH,
        unresolved=True,
        trl_ref="ev-003",
        threat_ref="ev-004",
    )
    report = agent.generate(
        run_id="run-test",
        merged_results=[m1, m2],
        priority_matrix=[_priority_row(m1), _priority_row(m2)],
        evidence_items=[
            _evidence("ev-001"),
            _evidence("ev-002", "Other content."),
            _evidence("ev-003", "Third content."),
            _evidence("ev-004", "Fourth content."),
        ],
    )
    summary = next(s for s in report.sections if s.section_id == "summary")
    assert "본 보고서는" in summary.body
    assert "즉각 대응" in summary.body or "전략적 감시" in summary.body
    assert "추가 검색과 근거 보강" in summary.body
    assert len(summary.body) >= 300


# ---------------------------------------------------------------------------
# Tests: reference trace
# ---------------------------------------------------------------------------

def test_reference_trace_populated(tmp_path: Path):
    agent = _make_agent(tmp_path)
    m = _merged(trl_ref="ev-001", threat_ref="ev-002")
    ev1 = _evidence("ev-001", "Raw content one.")
    ev2 = _evidence("ev-002", "Raw content two.")
    report = agent.generate(
        run_id="run-test",
        merged_results=[m],
        priority_matrix=[_priority_row(m)],
        evidence_items=[ev1, ev2],
    )
    assert len(report.reference_trace) > 0
    trace_ids = {t.evidence_id for t in report.reference_trace}
    assert "ev-001" in trace_ids
    assert "ev-002" in trace_ids


def test_reference_trace_no_duplicate_claim_evidence_pairs(tmp_path: Path):
    agent = _make_agent(tmp_path)
    m = _merged(trl_ref="ev-001", threat_ref="ev-001")
    report = agent.generate(
        run_id="run-test",
        merged_results=[m],
        priority_matrix=[_priority_row(m)],
        evidence_items=[_evidence("ev-001")],
    )
    pairs = [(t.claim_id, t.evidence_id) for t in report.reference_trace]
    assert len(pairs) == len(set(pairs))


# ---------------------------------------------------------------------------
# Tests: limitation / warning
# ---------------------------------------------------------------------------

def test_trl_limitation_notice_in_background_section(tmp_path: Path):
    agent = _make_agent(tmp_path)
    m = _merged()
    report = agent.generate(
        run_id="run-test",
        merged_results=[m],
        priority_matrix=[_priority_row(m)],
    )
    bg = next(s for s in report.sections if s.section_id == "background")
    assert "TRL 4~6" in bg.body


def test_threat_composite_notice_in_background_section(tmp_path: Path):
    agent = _make_agent(tmp_path)
    m = _merged()
    report = agent.generate(
        run_id="run-test",
        merged_results=[m],
        priority_matrix=[_priority_row(m)],
    )
    bg = next(s for s in report.sections if s.section_id == "background")
    assert "복합 요인" in bg.body


def test_unresolved_warning_generated(tmp_path: Path):
    agent = _make_agent(tmp_path)
    m = _merged(unresolved=True, priority_bucket=PriorityBucket.REVIEW_REQUIRED)
    report = agent.generate(
        run_id="run-test",
        merged_results=[m],
        priority_matrix=[_priority_row(m)],
    )
    codes = {w.code for w in report.warnings}
    assert "UNRESOLVED_CELL" in codes


def test_conflict_warning_generated(tmp_path: Path):
    agent = _make_agent(tmp_path)
    m = _merged(conflict_flag=True, priority_bucket=PriorityBucket.REVIEW_REQUIRED)
    report = agent.generate(
        run_id="run-test",
        merged_results=[m],
        priority_matrix=[_priority_row(m)],
    )
    codes = {w.code for w in report.warnings}
    assert "CONFLICT_FLAG" in codes


def test_missing_evidence_warning_generated_for_coverage_gap(tmp_path: Path):
    agent = _make_agent(tmp_path)
    m = _merged(
        data_status="coverage_gap",
        trl_ref=None,
        threat_ref=None,
        priority_bucket=PriorityBucket.REVIEW_REQUIRED,
    )
    report = agent.generate(
        run_id="run-test",
        merged_results=[m],
        priority_matrix=[_priority_row(m)],
    )
    codes = {w.code for w in report.warnings}
    assert "MISSING_EVIDENCE" in codes


# ---------------------------------------------------------------------------
# Tests: TRL-Threat divergence
# ---------------------------------------------------------------------------

def test_trl_threat_divergence_detected(tmp_path: Path):
    """TRL 4-5 vs HIGH threat → divergence warning and explanation in body."""
    agent = _make_agent(tmp_path)
    # TRL high=5, threat=HIGH(8) → |5-8|=3 >= threshold
    m = _merged(trl_range="4-5", threat_level=ThreatLevel.HIGH, priority_bucket=PriorityBucket.EMERGING_RISK)
    report = agent.generate(
        run_id="run-test",
        merged_results=[m],
        priority_matrix=[_priority_row(m)],
    )
    codes = {w.code for w in report.warnings}
    assert "TRL_THREAT_DIVERGENCE" in codes

    # Divergence explanation should appear in technology_status or competitor_trends sections
    full_text = " ".join(
        s.body + " " + " ".join(sub.body for sub in s.subsections)
        for s in report.sections
    )
    assert "괴리" in full_text or "Execution Credibility" in full_text


def test_no_divergence_when_trl_and_threat_aligned(tmp_path: Path):
    """TRL 7-8 vs HIGH threat → no divergence warning."""
    agent = _make_agent(tmp_path)
    m = _merged(trl_range="7-8", threat_level=ThreatLevel.HIGH, priority_bucket=PriorityBucket.IMMEDIATE_PRIORITY)
    report = agent.generate(
        run_id="run-test",
        merged_results=[m],
        priority_matrix=[_priority_row(m)],
    )
    codes = {w.code for w in report.warnings}
    assert "TRL_THREAT_DIVERGENCE" not in codes


# ---------------------------------------------------------------------------
# Tests: priority matrix in report
# ---------------------------------------------------------------------------

def test_strategic_implications_contains_priority_items(tmp_path: Path):
    agent = _make_agent(tmp_path)
    m = _merged(priority_bucket=PriorityBucket.IMMEDIATE_PRIORITY)
    report = agent.generate(
        run_id="run-test",
        merged_results=[m],
        priority_matrix=[_priority_row(m)],
    )
    si = next(s for s in report.sections if s.section_id == "strategic_implications")
    assert "immediate_priority" in si.body.lower() or "즉각" in si.body


# ---------------------------------------------------------------------------
# Tests: output file saved
# ---------------------------------------------------------------------------

def test_markdown_output_file_created(tmp_path: Path):
    agent = _make_agent(tmp_path)
    m = _merged()
    report = agent.generate(
        run_id="run-test",
        merged_results=[m],
        priority_matrix=[_priority_row(m)],
        output_format=ReportFormat.MARKDOWN,
    )
    assert Path(report.output_path).exists()
    content = Path(report.output_path).read_text(encoding="utf-8")
    assert "SUMMARY" in content
    assert "REFERENCE" in content


def test_html_output_file_created(tmp_path: Path):
    agent = _make_agent(tmp_path)
    m = _merged()
    report = agent.generate(
        run_id="run-test",
        merged_results=[m],
        priority_matrix=[_priority_row(m)],
        output_format=ReportFormat.HTML,
    )
    assert report.html_path != ""
    assert Path(report.html_path).exists()


def test_pdf_output_file_created(tmp_path: Path):
    agent = _make_agent(tmp_path)
    m = _merged()
    report = agent.generate(
        run_id="run-test",
        merged_results=[m],
        priority_matrix=[_priority_row(m)],
        output_format=ReportFormat.PDF,
    )
    assert report.pdf_path.endswith(".pdf")
    assert Path(report.pdf_path).exists()
    assert Path(report.output_path).suffix == ".pdf"


def test_coverage_gap_section_collects_evidence_poor_cells(tmp_path: Path):
    agent = _make_agent(tmp_path)
    ready = _merged(company="CompanyA")
    gap = _merged(
        company="CompanyB",
        data_status="coverage_gap",
        trl_ref=None,
        threat_ref=None,
        priority_bucket=PriorityBucket.REVIEW_REQUIRED,
    )
    report = agent.generate(
        run_id="run-test",
        merged_results=[ready, gap],
        priority_matrix=[_priority_row(ready), _priority_row(gap)],
        evidence_items=[_evidence("ev-001"), _evidence("ev-002", "Other content.")],
    )
    coverage_section = next(s for s in report.sections if s.section_id == "coverage_gap")
    assert "HBM4/CompanyB" in coverage_section.body

    tech_section = next(s for s in report.sections if s.section_id == "technology_status")
    full_sub_text = " ".join(sub.body for sub in tech_section.subsections)
    assert "CompanyB" not in full_sub_text


# ---------------------------------------------------------------------------
# Tests: status
# ---------------------------------------------------------------------------

def test_status_ready_when_no_warnings(tmp_path: Path):
    agent = _make_agent(tmp_path)
    # trl_range="5-6" → high=6, MEDIUM numeric=5 → |6-5|=1 < threshold(3) → no divergence warning
    m = _merged(
        trl_range="5-6",
        threat_level=ThreatLevel.MEDIUM,
        confidence=ConfidenceLevel.HIGH,
        conflict_flag=False,
        unresolved=False,
        priority_bucket=PriorityBucket.MONITOR,
    )
    report = agent.generate(
        run_id="run-test",
        merged_results=[m],
        priority_matrix=[_priority_row(m)],
    )
    assert report.status == ReportStatus.READY


def test_status_blocked_when_all_unresolved(tmp_path: Path):
    """When every merged result is unresolved, the report is BLOCKED (no usable analysis)."""
    agent = _make_agent(tmp_path)
    m = _merged(unresolved=True, priority_bucket=PriorityBucket.REVIEW_REQUIRED)
    report = agent.generate(
        run_id="run-test",
        merged_results=[m],
        priority_matrix=[_priority_row(m)],
    )
    assert report.status == ReportStatus.BLOCKED


def test_status_blocked_when_all_cells_are_coverage_gap(tmp_path: Path):
    agent = _make_agent(tmp_path)
    m = _merged(
        data_status="coverage_gap",
        unresolved=False,
        trl_ref=None,
        threat_ref=None,
        priority_bucket=PriorityBucket.REVIEW_REQUIRED,
    )
    report = agent.generate(
        run_id="run-test",
        merged_results=[m],
        priority_matrix=[_priority_row(m)],
    )
    assert report.status == ReportStatus.BLOCKED


def test_status_warning_when_one_of_two_unresolved(tmp_path: Path):
    """When only some results are unresolved, status is WARNING (report still generated)."""
    agent = _make_agent(tmp_path)
    m1 = _merged(company="CompanyA", unresolved=True, priority_bucket=PriorityBucket.REVIEW_REQUIRED)
    m2 = _merged(company="CompanyB", unresolved=False, trl_range="5-6",
                 threat_level=ThreatLevel.MEDIUM, priority_bucket=PriorityBucket.MONITOR)
    report = agent.generate(
        run_id="run-test",
        merged_results=[m1, m2],
        priority_matrix=[_priority_row(m1), _priority_row(m2)],
    )
    assert report.status == ReportStatus.WARNING
