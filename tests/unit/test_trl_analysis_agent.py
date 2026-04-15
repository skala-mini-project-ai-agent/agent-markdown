from src.agents.analysis.trl_analysis_agent import TRLAnalysisAgent


def test_trl_agent_prefers_direct_evidence_over_indirect():
    agent = TRLAnalysisAgent()
    evidence = [
        {
            "evidence_id": "d1",
            "run_id": "r1",
            "technology": "HBM4",
            "company": ["Company A"],
            "title": "Mass production and qualification complete",
            "signal_type": "direct",
            "source_type": "press_release",
            "published_at": "2025-01-01T00:00:00Z",
            "raw_content": "qualified supplier and shipping begins",
            "key_points": ["mass production"],
            "signals": ["qualification"],
            "counter_signals": [],
            "quality_passed": True,
        },
        {
            "evidence_id": "i1",
            "run_id": "r1",
            "technology": "HBM4",
            "company": ["Company A"],
            "title": "Patent filing",
            "signal_type": "indirect",
            "source_type": "patent",
            "published_at": "2025-01-01T00:00:00Z",
            "raw_content": "patent",
            "key_points": ["patent"],
            "signals": [],
            "counter_signals": [],
            "quality_passed": True,
        },
    ]

    result = agent.analyze(run_id="r1", technology="HBM4", company="Company A", evidence_items=evidence)

    assert result.unresolved is False
    assert result.trl_score_low >= 8
    assert "d1" in result.direct_evidence_ids
    assert "i1" in result.indirect_evidence_ids


def test_trl_agent_marks_weak_indirect_only_cells_unresolved():
    agent = TRLAnalysisAgent()
    evidence = [
        {
            "evidence_id": "i1",
            "run_id": "r1",
            "technology": "CXL",
            "company": ["Company A"],
            "title": "Conference talk about future memory interconnect",
            "signal_type": "indirect",
            "source_type": "conference",
            "published_at": "2024-05-01T00:00:00Z",
            "raw_content": "conference",
            "key_points": ["conference"],
            "signals": [],
            "counter_signals": [],
            "quality_passed": True,
        }
    ]

    result = agent.analyze(run_id="r1", technology="CXL", company="Company A", evidence_items=evidence)

    assert result.unresolved is False
    assert result.trl_score_low == 4
    assert result.trl_score_high == 6


def test_trl_agent_marks_no_matching_evidence_as_no_data():
    agent = TRLAnalysisAgent()
    evidence = [
        {
            "evidence_id": "i1",
            "run_id": "r1",
            "technology": "CXL",
            "company": ["Company B"],
            "title": "Conference talk",
            "signal_type": "indirect",
            "source_type": "conference",
            "published_at": "2024-05-01T00:00:00Z",
            "raw_content": "conference",
            "key_points": ["conference"],
            "signals": [],
            "counter_signals": [],
            "quality_passed": True,
        }
    ]

    result = agent.analyze(run_id="r1", technology="HBM4", company="Company A", evidence_items=evidence)

    assert result.data_status == "no_data"
    assert result.trl_range == "no_data"
    assert result.unresolved is False


def test_trl_agent_marks_quality_failed_match_as_coverage_gap():
    agent = TRLAnalysisAgent()
    evidence = [
        {
            "evidence_id": "i1",
            "run_id": "r1",
            "technology": "HBM4",
            "company": ["Company A"],
            "title": "Qualification progress",
            "signal_type": "direct",
            "source_type": "news",
            "published_at": "2025-05-01T00:00:00Z",
            "raw_content": "qualification",
            "key_points": ["qualification"],
            "signals": ["qualification"],
            "counter_signals": [],
            "quality_passed": False,
        }
    ]

    result = agent.analyze(run_id="r1", technology="HBM4", company="Company A", evidence_items=evidence)

    assert result.data_status == "coverage_gap"
    assert result.trl_range == "coverage_gap"
    assert result.unresolved is False
