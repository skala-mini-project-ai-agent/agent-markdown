"""Integration test: merge_node → ReportGenerationAgent → ReportRepository pipeline."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from src.agents.analysis.report_generation_agent import ReportGenerationAgent
from src.config.report_sections import SECTION_IDS
from src.orchestration.merge_node import merge_analysis_results
from src.schemas.analysis_output_schema import (
    ConfidenceLevel,
    ThreatAnalysisResult,
    ThreatLevel,
    ThreatTier,
    TRLAnalysisResult,
)
from src.schemas.normalized_evidence_schema import NormalizedEvidence
from src.schemas.report_output_schema import ReportFormat
from src.storage.repositories.report_repository import ReportRepository


def _trl(technology: str, company: str) -> TRLAnalysisResult:
    return TRLAnalysisResult(
        run_id="run-integration",
        technology=technology,
        company=company,
        trl_range="6-7",
        trl_score_low=6,
        trl_score_high=7,
        confidence=ConfidenceLevel.MEDIUM,
        rationale="Prototype validation and tape-out confirmed.",
        direct_evidence_ids=["ev-d1"],
        indirect_evidence_ids=["ev-i1"],
        evidence_ids=["ev-d1", "ev-i1"],
        unresolved=False,
        quality_passed=True,
    )


def _threat(technology: str, company: str) -> ThreatAnalysisResult:
    return ThreatAnalysisResult(
        run_id="run-integration",
        technology=technology,
        company=company,
        threat_level=ThreatLevel.HIGH,
        threat_tier=ThreatTier.TIER_1,
        impact_score=8,
        immediacy_score=7,
        execution_credibility_score=6,
        strategic_overlap_score=5,
        confidence=ConfidenceLevel.MEDIUM,
        rationale="High market impact with near-term execution signal.",
        evidence_ids=["ev-d1"],
    )


def _evidence(eid: str, tech: str, company: str) -> NormalizedEvidence:
    return NormalizedEvidence(
        evidence_id=eid,
        run_id="run-integration",
        agent_type=tech.lower(),
        technology=tech,
        company=[company],
        title=f"Evidence {eid}",
        source_type="paper",
        signal_type="direct",
        source_name="IEEE",
        published_at="2025-06-01T00:00:00Z",
        url=f"https://example.com/{eid}",
        raw_content=f"Full raw content for evidence {eid}. This is detailed technical information.",
        key_points=["key finding"],
        signals=["positive signal"],
        quality_passed=True,
    )


def test_full_pipeline_from_merge_to_report(tmp_path: Path):
    # Step 1: merge analysis results
    trl_results = [_trl("HBM4", "CompanyX"), _trl("CXL", "CompanyY")]
    threat_results = [_threat("HBM4", "CompanyX"), _threat("CXL", "CompanyY")]
    merged_results, priority_matrix = merge_analysis_results(trl_results, threat_results)

    # Step 2: generate report
    agent = ReportGenerationAgent(output_dir=tmp_path / "reports")
    evidence_items = [
        _evidence("ev-d1", "HBM4", "CompanyX"),
        _evidence("ev-i1", "HBM4", "CompanyX"),
    ]
    report = agent.generate(
        run_id="run-integration",
        merged_results=merged_results,
        priority_matrix=priority_matrix,
        evidence_items=evidence_items,
        output_format=ReportFormat.MARKDOWN,
    )

    # Step 3: persist to repository
    db_path = tmp_path / "reports.db"
    repo = ReportRepository(database_path=db_path)
    repo.save(report)

    # Assertions: all required sections present
    section_ids = {s.section_id for s in report.sections}
    for sid in SECTION_IDS:
        assert sid in section_ids, f"Missing section: {sid}"

    # Assertions: output file exists and has content
    md_path = Path(report.output_path)
    assert md_path.exists()
    content = md_path.read_text(encoding="utf-8")
    assert "SUMMARY" in content
    assert "REFERENCE" in content
    assert "기술 현황" in content
    assert "경쟁사 동향" in content

    # Assertions: reference trace populated
    assert len(report.reference_trace) > 0

    # Assertions: repository round-trip
    fetched = repo.get(report.report_id)
    assert fetched is not None
    assert fetched.run_id == "run-integration"
    assert len(fetched.sections) == len(report.sections)

    # Assertions: list_by_run works
    reports = repo.list_by_run("run-integration")
    assert len(reports) >= 1
    assert reports[0].report_id == report.report_id


def test_report_with_unresolved_cells_has_warning(tmp_path: Path):
    trl_unresolved = TRLAnalysisResult(
        run_id="run-integration2",
        technology="PIM",
        company="CorpZ",
        trl_range="unresolved",
        trl_score_low=None,
        trl_score_high=None,
        confidence=ConfidenceLevel.LOW,
        rationale="No evidence matched.",
        unresolved=True,
        quality_passed=True,
    )
    threat_unresolved = ThreatAnalysisResult(
        run_id="run-integration2",
        technology="PIM",
        company="CorpZ",
        threat_level=ThreatLevel.LOW,
        threat_tier=ThreatTier.TIER_3,
        impact_score=2,
        immediacy_score=2,
        execution_credibility_score=2,
        strategic_overlap_score=1,
        confidence=ConfidenceLevel.LOW,
        rationale="Insufficient evidence.",
        unresolved=True,
    )
    merged, priority = merge_analysis_results([trl_unresolved], [threat_unresolved])

    agent = ReportGenerationAgent(output_dir=tmp_path / "reports2")
    report = agent.generate(
        run_id="run-integration2",
        merged_results=merged,
        priority_matrix=priority,
    )

    codes = {w.code for w in report.warnings}
    assert "UNRESOLVED_CELL" in codes
