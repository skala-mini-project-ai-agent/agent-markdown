import pytest

from src.agents.analysis.trl_analysis_agent import TRLAnalysisAgent
from src.agents.analysis.threat_analysis_agent import ThreatAnalysisAgent
from src.orchestration.merge_node import AnalysisMergeError, merge_analysis_results
from src.schemas.analysis_output_schema import ThreatAnalysisResult


def test_merge_node_is_deterministic():
    trl_agent = TRLAnalysisAgent()
    threat_agent = ThreatAnalysisAgent()
    evidence = [
        {
            "evidence_id": "e1",
            "run_id": "r1",
            "technology": "HBM4",
            "company": ["Company A"],
            "title": "Mass production and qualification complete",
            "signal_type": "direct",
            "source_type": "filing",
            "published_at": "2025-01-01T00:00:00Z",
            "raw_content": "mass production",
            "key_points": ["mass production"],
            "signals": ["qualification"],
            "counter_signals": [],
            "quality_passed": True,
        }
    ]
    trl = trl_agent.analyze(run_id="r1", technology="HBM4", company="Company A", evidence_items=evidence)
    threat = threat_agent.analyze(run_id="r1", technology="HBM4", company="Company A", evidence_items=evidence, trl_result=trl)

    merged_a, rows_a = merge_analysis_results([trl], [threat])
    merged_b, rows_b = merge_analysis_results([trl], [threat])

    assert merged_a[0].to_dict() == merged_b[0].to_dict()
    assert rows_a[0].to_dict() == rows_b[0].to_dict()


def test_merge_node_raises_on_key_mismatch():
    trl_agent = TRLAnalysisAgent()
    threat_agent = ThreatAnalysisAgent()
    evidence = [
        {
            "evidence_id": "e1",
            "run_id": "r1",
            "technology": "HBM4",
            "company": ["Company A"],
            "title": "Engineering sample",
            "signal_type": "direct",
            "source_type": "filing",
            "published_at": "2025-01-01T00:00:00Z",
            "raw_content": "engineering sample",
            "key_points": ["engineering sample"],
            "signals": [],
            "counter_signals": [],
            "quality_passed": True,
        }
    ]
    trl = trl_agent.analyze(run_id="r1", technology="HBM4", company="Company A", evidence_items=evidence)
    threat = threat_agent.analyze(run_id="r1", technology="HBM4", company="Company A", evidence_items=evidence, trl_result=trl)
    threat = ThreatAnalysisResult.from_dict({**threat.to_dict(), "company": "Company B"})

    with pytest.raises(AnalysisMergeError):
        merge_analysis_results([trl], [threat])


def test_merge_node_preserves_coverage_gap_without_forcing_conflict():
    trl = TRLAnalysisAgent().analyze(
        run_id="r1",
        technology="HBM4",
        company="Company A",
        evidence_items=[
            {
                "evidence_id": "e1",
                "run_id": "r1",
                "technology": "HBM4",
                "company": ["Company A"],
                "title": "Qualification progress",
                "signal_type": "direct",
                "source_type": "news",
                "published_at": "2025-01-01T00:00:00Z",
                "raw_content": "qualification",
                "key_points": ["qualification"],
                "signals": [],
                "counter_signals": [],
                "quality_passed": False,
            }
        ],
    )
    threat = ThreatAnalysisAgent().analyze(
        run_id="r1",
        technology="HBM4",
        company="Company A",
        evidence_items=[
            {
                "evidence_id": "e1",
                "run_id": "r1",
                "technology": "HBM4",
                "company": ["Company A"],
                "title": "Qualification progress",
                "signal_type": "direct",
                "source_type": "news",
                "published_at": "2025-01-01T00:00:00Z",
                "raw_content": "qualification",
                "key_points": ["qualification"],
                "signals": [],
                "counter_signals": [],
                "quality_passed": False,
            }
        ],
        trl_result=trl,
    )

    merged, rows = merge_analysis_results([trl], [threat])

    assert merged[0].data_status == "coverage_gap"
    assert merged[0].conflict_flag is False
    assert rows[0].priority_bucket.value == "review_required"
