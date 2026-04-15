from src.agents.analysis.trl_analysis_agent import TRLAnalysisAgent
from src.agents.analysis.threat_analysis_agent import ThreatAnalysisAgent
from src.orchestration.merge_node import merge_analysis_results
from src.schemas.analysis_output_schema import PriorityBucket


def test_priority_bucket_rules_cover_high_threat_and_high_overlap():
    trl_agent = TRLAnalysisAgent()
    threat_agent = ThreatAnalysisAgent()
    evidence = [
        {
            "evidence_id": "e1",
            "run_id": "r1",
            "technology": "HBM4",
            "company": ["Samsung"],
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
    trl = trl_agent.analyze(run_id="r1", technology="HBM4", company="Samsung", evidence_items=evidence)
    threat = threat_agent.analyze(run_id="r1", technology="HBM4", company="Samsung", evidence_items=evidence, trl_result=trl)
    merged, rows = merge_analysis_results([trl], [threat])

    assert merged[0].priority_bucket in {PriorityBucket.IMMEDIATE_PRIORITY, PriorityBucket.STRATEGIC_WATCH, PriorityBucket.MONITOR}
    assert rows[0].priority_bucket == merged[0].priority_bucket
