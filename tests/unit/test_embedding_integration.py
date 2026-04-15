from src.agents.analysis.report_generation_agent import ReportGenerationAgent
from src.config.settings import SupervisorSettings
from src.providers.embedding.base_embedding_provider import BaseEmbeddingProvider
from src.retrieval.evidence_retriever import attach_embeddings
from src.schemas.analysis_output_schema import ConfidenceLevel, MergedAnalysisResult, PriorityBucket, ThreatLevel
from src.schemas.normalized_evidence_schema import NormalizedEvidence
from src.supervisor.retry_controller import RetryController


class FakeEmbeddingProvider(BaseEmbeddingProvider):
    def embed_texts(self, texts: list[str], *, task: str = "retrieval") -> list[list[float]]:
        vectors = []
        for text in texts:
            lowered = text.lower()
            score = 3.0 if "qualification" in lowered else 1.0
            extra = 2.0 if "companya" in lowered else 1.0
            vectors.append([score, extra])
        return vectors


def _evidence(evidence_id: str, company: str = "CompanyA") -> NormalizedEvidence:
    return NormalizedEvidence(
        evidence_id=evidence_id,
        run_id="run-1",
        agent_type="hbm4",
        technology="HBM4",
        company=[company],
        title=f"Evidence {evidence_id}",
        source_type="paper",
        signal_type="direct",
        source_name="IEEE",
        published_at="2025-01-01T00:00:00Z",
        url=f"https://example.com/{evidence_id}",
        raw_content="customer qualification complete",
        key_points=["qualification"],
        signals=["qualification"],
        quality_passed=True,
    )


def test_attach_embeddings_populates_metadata():
    provider = FakeEmbeddingProvider()
    items = [_evidence("ev1")]
    attach_embeddings(items, embedding_provider=provider)
    assert "embedding" in items[0].metadata


def test_retry_controller_adds_expansion_terms():
    provider = FakeEmbeddingProvider()
    items = [_evidence("ev1")]
    attach_embeddings(items, embedding_provider=provider)

    class Quality:
        low_evidence_cells = [{"technology": "HBM4", "company": "CompanyA", "reason": "low_evidence"}]
        low_confidence_cells = []
        conflict_flags = []
        bias_flags = []

    plan = RetryController(SupervisorSettings(), embedding_provider=provider).build_retry_plan(
        run_id="r1",
        quality_report=Quality(),
        current_retry_count=0,
        evidence_items=items,
    )

    assert plan.retry_targets
    assert plan.retry_targets[0].expansion_terms


def test_report_generation_uses_semantic_trace_when_reference_ids_missing(tmp_path):
    provider = FakeEmbeddingProvider()
    evidence = _evidence("ev1")
    attach_embeddings([evidence], embedding_provider=provider)
    merged = MergedAnalysisResult(
        run_id="run-1",
        technology="HBM4",
        company="CompanyA",
        trl_range="6-7",
        threat_level=ThreatLevel.HIGH,
        merged_confidence=ConfidenceLevel.MEDIUM,
        conflict_flag=False,
        priority_bucket=PriorityBucket.STRATEGIC_WATCH,
        action_hint="Monitor strategically.",
        trl_reference_id=None,
        threat_reference_id=None,
    )
    report = ReportGenerationAgent(output_dir=tmp_path, embedding_provider=provider).generate(
        run_id="run-1",
        merged_results=[merged],
        priority_matrix=[],
        evidence_items=[evidence],
    )
    assert report.reference_trace
