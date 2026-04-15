from src.agents.base.base_agent import SearchExecutionContext
from src.agents.search.hbm4_search_agent import HBM4SearchAgent
from src.providers.search.deterministic_search_provider import DeterministicSearchProvider


def test_retry_query_adds_quality_terms_and_hints():
    agent = HBM4SearchAgent(provider=DeterministicSearchProvider())
    context = SearchExecutionContext(
        run_id="run-1",
        user_query="HBM4 strategic scan",
        metadata={
            "retry_attempt": 1,
            "retry_plan": {
                "retry_targets": [
                    {"agent": "hbm4", "technology": "HBM4", "company": "SK hynix", "reason": "low_confidence"}
                ]
            },
        },
    )

    queries = agent.build_queries(context)

    assert any("validated benchmark customer qualification" in query.query for query in queries)
    assert any("conference" in query.source_hints for query in queries)


def test_search_run_propagates_local_validation_to_findings():
    agent = HBM4SearchAgent(provider=DeterministicSearchProvider())
    context = SearchExecutionContext(run_id="run-2", user_query="HBM4 strategic scan")

    bundle = agent.run(context)

    assert bundle.local_validation["passed"] is True
    assert bundle.raw_findings
    assert all("passed" in finding.local_validation for finding in bundle.raw_findings)
    assert all(finding.local_validation["passed"] is True for finding in bundle.raw_findings)
