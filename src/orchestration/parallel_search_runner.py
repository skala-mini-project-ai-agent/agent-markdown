"""Parallel search runner for search owner scope."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from src.agents.base.base_agent import SearchExecutionContext
from src.agents.search.cxl_search_agent import CXLSearchAgent
from src.agents.search.hbm4_search_agent import HBM4SearchAgent
from src.agents.search.indirect_signal_patent_agent import IndirectSignalPatentSearchAgent
from src.agents.search.packaging_interconnect_agent import PackagingInterconnectSearchAgent
from src.agents.search.pim_search_agent import PIMSearchAgent
from src.agents.search.thermal_power_agent import ThermalPowerSearchAgent
from src.normalization.evidence_loader import EvidenceLoader
from src.normalization.evidence_normalizer import EvidenceNormalizer
from src.providers.search.base_search_provider import BaseSearchProvider
from src.providers.search.deterministic_search_provider import DeterministicSearchProvider
from src.quality.quality_gate import QualityGate
from src.schemas.normalized_evidence_schema import NormalizedEvidence
from src.schemas.quality_report_schema import QualityReport
from src.schemas.raw_result_schema import RawSearchBundle
from src.storage.repositories.normalized_evidence_repository import NormalizedEvidenceRepository
from src.storage.repositories.quality_report_repository import QualityReportRepository
from src.storage.repositories.raw_finding_repository import RawFindingRepository


@dataclass(slots=True)
class AgentRunStatus:
    status: str
    bundle: RawSearchBundle | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ParallelSearchRunResult:
    run_id: str
    executed_at: str
    agents: dict[str, AgentRunStatus] = field(default_factory=dict)
    normalized_evidence: list[NormalizedEvidence] = field(default_factory=list)
    quality_report: QualityReport | None = None


class ParallelSearchRunner:
    def __init__(
        self,
        agents: dict[str, Any] | None = None,
        *,
        provider: BaseSearchProvider | None = None,
        raw_repository: RawFindingRepository | None = None,
        normalized_repository: NormalizedEvidenceRepository | None = None,
        quality_repository: QualityReportRepository | None = None,
        normalizer: EvidenceNormalizer | None = None,
        quality_gate: QualityGate | None = None,
        loader: EvidenceLoader | None = None,
    ) -> None:
        self.provider = provider or DeterministicSearchProvider()
        self.agents = agents or self._default_agents()
        self.raw_repository = raw_repository or RawFindingRepository()
        self.normalized_repository = normalized_repository or NormalizedEvidenceRepository()
        self.quality_repository = quality_repository or QualityReportRepository()
        self.normalizer = normalizer or EvidenceNormalizer()
        self.quality_gate = quality_gate or QualityGate()
        self.loader = loader or EvidenceLoader(self.normalized_repository)

    def _default_agents(self) -> dict[str, Any]:
        return {
            "pim": PIMSearchAgent(provider=self.provider),
            "cxl": CXLSearchAgent(provider=self.provider),
            "hbm4": HBM4SearchAgent(provider=self.provider),
            "packaging": PackagingInterconnectSearchAgent(provider=self.provider),
            "thermal_power": ThermalPowerSearchAgent(provider=self.provider),
            "indirect_signal": IndirectSignalPatentSearchAgent(provider=self.provider),
        }

    def run(self, context: SearchExecutionContext) -> ParallelSearchRunResult:
        executed_at = datetime.now(timezone.utc).isoformat()
        result = ParallelSearchRunResult(run_id=context.run_id, executed_at=executed_at)

        with ThreadPoolExecutor(max_workers=len(self.agents) or 1) as executor:
            futures = {executor.submit(agent.run, context): agent_type for agent_type, agent in self.agents.items()}
            for future in as_completed(futures):
                agent_type = futures[future]
                try:
                    bundle = future.result()
                    self.raw_repository.save_many(bundle.raw_findings)
                    result.agents[agent_type] = AgentRunStatus(status="success", bundle=bundle)
                except Exception as exc:  # pragma: no cover - defensive path
                    result.agents[agent_type] = AgentRunStatus(status="failed", error=str(exc))

        normalized: list[NormalizedEvidence] = []
        for agent_status in result.agents.values():
            if not agent_status.bundle:
                continue
            normalized.extend(self.normalizer.normalize_bundle(agent_status.bundle))
        self.loader.load(normalized)
        quality_report = self.quality_gate.evaluate(context.run_id, normalized)
        self.quality_repository.save(quality_report)

        result.normalized_evidence = normalized
        result.quality_report = quality_report
        return result
