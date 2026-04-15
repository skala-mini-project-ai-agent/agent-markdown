from src.agents.analysis.threat_analysis_agent import ThreatAnalysisAgent
from src.schemas.analysis_output_schema import ConfidenceLevel, TRLAnalysisResult


def test_threat_agent_scores_four_axes_and_detects_publicity_bias():
    agent = ThreatAnalysisAgent()
    evidence = [
        {
            "evidence_id": "e1",
            "run_id": "r1",
            "technology": "PIM",
            "company": ["Company A"],
            "title": "Press release on roadmap",
            "signal_type": "direct",
            "source_type": "press_release",
            "published_at": "2025-01-01T00:00:00Z",
            "raw_content": "announcement only",
            "key_points": ["announcement"],
            "signals": [],
            "counter_signals": [],
            "quality_passed": True,
        }
    ]
    trl = TRLAnalysisResult(
        run_id="r1",
        technology="PIM",
        company="Company A",
        trl_range="2-3",
        trl_score_low=2,
        trl_score_high=3,
        confidence=ConfidenceLevel.LOW,
        rationale="low TRL",
        unresolved=False,
    )

    result = agent.analyze(run_id="r1", technology="PIM", company="Company A", evidence_items=evidence, trl_result=trl)

    assert result.impact_score >= 3
    assert result.immediacy_score >= 3
    assert result.execution_credibility_score >= 3
    assert result.strategic_overlap_score >= 3
    assert result.has_conflict is True
    assert result.conflict_type in {"timeline_mismatch", "publicity_bias", "evidence_strength_mismatch"}
    assert result.confidence == ConfidenceLevel.LOW


def test_threat_agent_avoids_equating_low_trl_with_low_threat():
    agent = ThreatAnalysisAgent()
    evidence = [
        {
            "evidence_id": "e1",
            "run_id": "r1",
            "technology": "HBM4",
            "company": ["Company A"],
            "title": "Engineering sample and qualification progress",
            "signal_type": "direct",
            "source_type": "filing",
            "published_at": "2025-01-01T00:00:00Z",
            "raw_content": "qualification",
            "key_points": ["qualification"],
            "signals": [],
            "counter_signals": [],
            "quality_passed": True,
        }
    ]
    trl = TRLAnalysisResult(
        run_id="r1",
        technology="HBM4",
        company="Company A",
        trl_range="2-3",
        trl_score_low=2,
        trl_score_high=3,
        confidence=ConfidenceLevel.MEDIUM,
        rationale="early",
        unresolved=False,
    )

    result = agent.analyze(run_id="r1", technology="HBM4", company="Company A", evidence_items=evidence, trl_result=trl)

    assert result.threat_level.value in {"medium", "high"}
    assert result.has_conflict is False or result.conflict_type in {"timeline_mismatch", "evidence_strength_mismatch"}
