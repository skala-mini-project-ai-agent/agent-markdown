"""Retry planning for supervisor-managed quality failures."""

from __future__ import annotations

from dataclasses import dataclass

from ..config.settings import SupervisorSettings
from ..providers.embedding.base_embedding_provider import BaseEmbeddingProvider
from ..retrieval.evidence_retriever import extract_expansion_terms, top_k_similar_evidence
from ..schemas.normalized_evidence_schema import NormalizedEvidence
from ..schemas.supervisor_state_schema import RetryPlan, RetryTarget


TECH_TO_AGENT = {
    "HBM4": "hbm4",
    "PIM": "pim",
    "CXL": "cxl",
    "Advanced Packaging": "packaging",
    "Thermal·Power": "thermal_power",
    "Indirect Signal": "indirect_signal",
}


@dataclass(slots=True)
class RetryController:
    settings: SupervisorSettings
    embedding_provider: BaseEmbeddingProvider | None = None

    def build_retry_plan(
        self,
        *,
        run_id: str,
        quality_report: object,
        current_retry_count: int,
        evidence_items: list[NormalizedEvidence] | None = None,
    ) -> RetryPlan:
        cells = self._collect_retry_cells(quality_report)
        retry_allowed = current_retry_count < self.settings.max_retry_count and bool(cells)
        retry_count = current_retry_count + 1 if retry_allowed else current_retry_count
        targets = [
            RetryTarget(
                agent=TECH_TO_AGENT.get(cell.get("technology", ""), "unknown"),
                technology=cell.get("technology", ""),
                company=cell.get("company", ""),
                reason=str(cell.get("reason", "quality_gap")),
                source_type=cell.get("source_type"),
                expansion_terms=self._build_expansion_terms(cell, evidence_items or []),
            )
            for cell in cells
        ]
        return RetryPlan(
            run_id=run_id,
            retry_targets=targets,
            retry_allowed=retry_allowed,
            retry_count=retry_count,
            unresolved_allowed=not retry_allowed and self.settings.allow_unresolved_after_retry_limit,
        )

    def _collect_retry_cells(self, quality_report: object) -> list[dict[str, object]]:
        raw_cells: list[dict[str, object]] = []
        raw_cells.extend(list(getattr(quality_report, "low_evidence_cells", [])))
        raw_cells.extend(list(getattr(quality_report, "low_confidence_cells", [])))
        raw_cells.extend(self._from_conflicts(list(getattr(quality_report, "conflict_flags", []))))
        raw_cells.extend(self._from_bias_flags(list(getattr(quality_report, "bias_flags", []))))

        deduped: list[dict[str, object]] = []
        seen: set[tuple[str, str, str]] = set()
        for cell in raw_cells:
            technology = str(cell.get("technology", ""))
            company = str(cell.get("company", ""))
            reason = str(cell.get("reason", cell.get("type", "quality_gap")))
            key = (technology, company, reason)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(
                {
                    "technology": technology,
                    "company": company,
                    "reason": reason,
                    "source_type": cell.get("source_type"),
                }
            )
        return deduped

    def _from_conflicts(self, conflicts: list[dict[str, object]]) -> list[dict[str, object]]:
        cells: list[dict[str, object]] = []
        for conflict in conflicts:
            company_value = conflict.get("company", "")
            if isinstance(company_value, list):
                company = str(company_value[0]) if company_value else ""
            else:
                company = str(company_value)
            cells.append(
                {
                    "technology": str(conflict.get("technology", "")),
                    "company": company,
                    "reason": str(conflict.get("reason", "conflict")),
                }
            )
        return cells

    def _from_bias_flags(self, bias_flags: list[dict[str, object]]) -> list[dict[str, object]]:
        cells: list[dict[str, object]] = []
        for flag in bias_flags:
            if flag.get("type") == "company_bias":
                cells.append(
                    {
                        "technology": "",
                        "company": str(flag.get("company", "")),
                        "reason": "company_bias",
                    }
                )
        return cells

    def _build_expansion_terms(
        self,
        cell: dict[str, object],
        evidence_items: list[NormalizedEvidence],
    ) -> list[str]:
        technology = str(cell.get("technology", ""))
        company = str(cell.get("company", ""))
        scoped = [
            item
            for item in evidence_items
            if (not technology or item.technology == technology) and (not company or company in item.company)
        ]
        if not scoped:
            return []
        if self.embedding_provider and hasattr(self.embedding_provider, "embed_texts"):
            query_text = f"{technology} {company} {cell.get('reason', 'quality_gap')}".strip()
            vector = self.embedding_provider.embed_texts([query_text], task="retrieval.query")[0]
            ranked = top_k_similar_evidence(
                vector,
                scoped,
                technology=technology or None,
                company=company or None,
                top_k=3,
            )
            scoped = [item for item, score in ranked if score > 0] or scoped
        return extract_expansion_terms(scoped)
