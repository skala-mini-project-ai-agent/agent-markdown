"""Top-level quality gate for normalized evidence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from src.quality.bias_detection import detect_bias
from src.quality.confidence_evaluator import evaluate_low_confidence_cells
from src.quality.conflict_detection import detect_conflicts
from src.quality.coverage_matrix import build_coverage_matrix, count_cells_below_threshold
from src.quality.deduplication import deduplicate_evidence
from src.quality.source_diversity import evaluate_source_diversity
from src.schemas.normalized_evidence_schema import NormalizedEvidence
from src.schemas.quality_report_schema import QualityReport


@dataclass(slots=True)
class QualityGate:
    coverage_threshold: int = 2

    def evaluate(self, run_id: str, evidence: Iterable[NormalizedEvidence]) -> QualityReport:
        deduped, duplicates_removed = deduplicate_evidence(evidence)
        coverage = build_coverage_matrix(deduped)
        source_diversity = evaluate_source_diversity(deduped)
        bias_flags = detect_bias(deduped)
        conflict_flags = detect_conflicts(deduped)
        low_evidence_cells = count_cells_below_threshold(deduped, threshold=self.coverage_threshold)
        low_confidence_cells = evaluate_low_confidence_cells(deduped, threshold=self.coverage_threshold)

        retry_recommendations: list[dict[str, object]] = []
        for cell in low_evidence_cells:
            retry_recommendations.append(
                {
                    "technology": cell["technology"],
                    "company": cell["company"],
                    "action": "targeted_retry",
                }
            )

        status = "pass"
        if low_evidence_cells or not deduped:
            status = "fail"
        elif bias_flags or conflict_flags or low_confidence_cells:
            status = "warning"

        return QualityReport(
            run_id=run_id,
            status=status,
            coverage={
                "matrix": coverage,
                "total_records": len(deduped),
                "coverage_threshold": self.coverage_threshold,
            },
            source_diversity=source_diversity,
            duplicates_removed=duplicates_removed,
            bias_flags=bias_flags,
            conflict_flags=conflict_flags,
            low_evidence_cells=low_evidence_cells,
            low_confidence_cells=low_confidence_cells,
            retry_recommendations=retry_recommendations,
            analysis_ready=status == "pass",
        )

