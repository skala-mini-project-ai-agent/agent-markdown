"""Unit tests for reference trace logic in ReportGenerationAgent."""

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
from src.schemas.normalized_evidence_schema import NormalizedEvidence


def _make_merged(trl_ref: str | None, threat_ref: str | None) -> MergedAnalysisResult:
    return MergedAnalysisResult(
        run_id="run-trace",
        technology="CXL",
        company="CorpB",
        trl_range="5-6",
        threat_level=ThreatLevel.MEDIUM,
        merged_confidence=ConfidenceLevel.MEDIUM,
        conflict_flag=False,
        priority_bucket=PriorityBucket.MONITOR,
        action_hint="Monitor.",
        trl_reference_id=trl_ref,
        threat_reference_id=threat_ref,
    )


def _make_evidence(eid: str) -> NormalizedEvidence:
    return NormalizedEvidence(
        evidence_id=eid,
        run_id="run-trace",
        agent_type="cxl",
        technology="CXL",
        company=["CorpB"],
        title=f"Title {eid}",
        source_type="paper",
        signal_type="direct",
        source_name="ACM",
        published_at="2025-03-01T00:00:00Z",
        url=f"https://example.com/{eid}",
        raw_content=f"Raw content for {eid}.",
        quality_passed=True,
    )


def _make_priority_row(m: MergedAnalysisResult) -> PriorityMatrixRow:
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
    )


def test_trace_includes_source_name_and_url(tmp_path: Path):
    agent = ReportGenerationAgent(output_dir=tmp_path)
    m = _make_merged("ev-x", "ev-y")
    ev_x = _make_evidence("ev-x")
    ev_y = _make_evidence("ev-y")
    report = agent.generate(
        run_id="run-trace",
        merged_results=[m],
        priority_matrix=[_make_priority_row(m)],
        evidence_items=[ev_x, ev_y],
    )
    for trace in report.reference_trace:
        if trace.evidence_id == "ev-x":
            assert trace.source_name == "ACM"
            assert "ev-x" in trace.url
        if trace.evidence_id == "ev-y":
            assert trace.source_name == "ACM"


def test_trace_missing_evidence_still_included(tmp_path: Path):
    """When evidence_map doesn't contain the ref_id, trace entry is still created."""
    agent = ReportGenerationAgent(output_dir=tmp_path)
    m = _make_merged("ev-missing", None)
    report = agent.generate(
        run_id="run-trace",
        merged_results=[m],
        priority_matrix=[_make_priority_row(m)],
        evidence_items=[],  # no evidence provided
    )
    trace_ids = {t.evidence_id for t in report.reference_trace}
    assert "ev-missing" in trace_ids


def test_trace_quote_uses_raw_content(tmp_path: Path):
    agent = ReportGenerationAgent(output_dir=tmp_path)
    m = _make_merged("ev-q", None)
    ev = _make_evidence("ev-q")
    ev_with_long_content = NormalizedEvidence(
        evidence_id="ev-q",
        run_id="run-trace",
        agent_type="cxl",
        technology="CXL",
        company=["CorpB"],
        title="Long content evidence",
        source_type="paper",
        signal_type="direct",
        source_name="IEEE",
        published_at="2025-01-01T00:00:00Z",
        url="https://example.com/ev-q",
        raw_content="A" * 500,
        quality_passed=True,
    )
    report = agent.generate(
        run_id="run-trace",
        merged_results=[m],
        priority_matrix=[_make_priority_row(m)],
        evidence_items=[ev_with_long_content],
    )
    trace = next(t for t in report.reference_trace if t.evidence_id == "ev-q")
    # Quote is capped at 300 chars
    assert len(trace.quote) <= 300
    assert trace.quote.startswith("A")


def test_no_duplicate_traces(tmp_path: Path):
    agent = ReportGenerationAgent(output_dir=tmp_path)
    # Same ref for both trl and threat — different claim_ids, so two traces but no duplicated (claim,ev) pair
    m = _make_merged("ev-same", "ev-same")
    ev = _make_evidence("ev-same")
    report = agent.generate(
        run_id="run-trace",
        merged_results=[m],
        priority_matrix=[_make_priority_row(m)],
        evidence_items=[ev],
    )
    pairs = [(t.claim_id, t.evidence_id) for t in report.reference_trace]
    assert len(pairs) == len(set(pairs))
