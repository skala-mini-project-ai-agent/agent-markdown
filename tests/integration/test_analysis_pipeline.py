from src.agents.analysis.trl_analysis_agent import TRLAnalysisAgent
from src.agents.analysis.threat_analysis_agent import ThreatAnalysisAgent
from src.orchestration.merge_node import merge_analysis_results
from src.storage.repositories.analysis_result_repository import AnalysisResultRepository


def test_analysis_pipeline_roundtrip_persists_results():
    repo = AnalysisResultRepository()
    trl_agent = TRLAnalysisAgent()
    threat_agent = ThreatAnalysisAgent()
    evidence = [
        {
            "evidence_id": "e1",
            "run_id": "r1",
            "technology": "PIM",
            "company": ["Company A"],
            "title": "Engineering sample and pilot deployment",
            "signal_type": "direct",
            "source_type": "press_release",
            "published_at": "2025-01-01T00:00:00Z",
            "raw_content": "pilot deployment",
            "key_points": ["pilot"],
            "signals": ["deployment"],
            "counter_signals": [],
            "quality_passed": True,
        }
    ]

    trl = trl_agent.analyze(run_id="r1", technology="PIM", company="Company A", evidence_items=evidence)
    threat = threat_agent.analyze(run_id="r1", technology="PIM", company="Company A", evidence_items=evidence, trl_result=trl)
    merged, rows = merge_analysis_results([trl], [threat])

    repo.store_trl_result(trl)
    repo.store_threat_result(threat)
    repo.store_merged_result(merged[0])
    repo.store_priority_rows(rows)

    assert repo.get_trl_result("r1", "PIM", "Company A") is not None
    assert repo.get_threat_result("r1", "PIM", "Company A") is not None
    assert repo.get_merged_result("r1", "PIM", "Company A") is not None
    assert repo.list_priority_rows("r1")[0].priority_bucket == rows[0].priority_bucket
