"""Base search agent interface."""

from __future__ import annotations

from abc import ABC
from collections import Counter
from typing import Any

from src.agents.base.base_agent import AgentValidationResult, BaseAgent, SearchExecutionContext, utc_now_iso
from src.providers.search.base_search_provider import BaseSearchProvider
from src.schemas.raw_result_schema import RawFinding, RawSearchBundle, SearchQuery


class BaseSearchAgent(BaseAgent, ABC):
    technology: str = ""
    focus_terms: tuple[str, ...] = ()
    min_source_count: int = 2

    def __init__(self, *, provider: BaseSearchProvider | None = None) -> None:
        super().__init__(provider=provider)
        if provider is None:
            raise ValueError("BaseSearchAgent requires a search provider")

    def build_queries(self, context: SearchExecutionContext) -> list[SearchQuery]:
        queries: list[SearchQuery] = []
        terms = list(self.focus_terms)
        if terms:
            for term in terms[:3]:
                queries.append(
                    SearchQuery(
                        query=f"{context.user_query or self.technology} {term}".strip(),
                        technology=self.technology,
                        source_hints=["news", "press_release", "paper"],
                        metadata={"term": term, "agent_type": self.agent_type},
                    )
                )
        else:
            queries.append(
                SearchQuery(
                    query=context.user_query or self.technology,
                    technology=self.technology,
                    source_hints=["news", "press_release"],
                    metadata={"agent_type": self.agent_type},
                )
            )
        return queries

    def search(
        self,
        queries: list[SearchQuery],
        context: SearchExecutionContext,
    ) -> list[RawFinding]:
        raw_findings: list[RawFinding] = []
        for query in queries:
            raw_findings.extend(
                self.provider.search(
                    query,
                    run_id=context.run_id,
                    agent_type=self.agent_type,
                    context=context.to_dict(),
                )
            )
        return raw_findings

    def local_validate(self, raw_findings: list[RawFinding]) -> AgentValidationResult:
        source_names = {finding.source_name for finding in raw_findings if finding.source_name}
        urls = [finding.url for finding in raw_findings if finding.url]
        duplicate_urls = [url for url, count in Counter(urls).items() if count > 1]
        has_counter_signals = any(finding.counter_signals for finding in raw_findings)
        recentish = sum(1 for finding in raw_findings if finding.published_at >= f"{2024}-01-01")
        total = len(raw_findings)
        passed = total > 0 and len(source_names) >= self.min_source_count
        warnings = []
        if duplicate_urls:
            warnings.append("duplicate_urls_detected")
        if not has_counter_signals:
            warnings.append("counter_signals_missing")
        if total and recentish / total < 0.8:
            warnings.append("freshness_threshold_not_met")
        return AgentValidationResult(
            passed=passed,
            summary={
                "source_count": len(source_names),
                "total_findings": total,
                "duplicate_urls": duplicate_urls,
                "recentish_ratio": (recentish / total) if total else 0.0,
                "has_counter_signals": has_counter_signals,
            },
            warnings=warnings,
        )

    def to_raw_bundle(
        self,
        *,
        context: SearchExecutionContext,
        queries: list[SearchQuery],
        raw_findings: list[RawFinding],
        validation: AgentValidationResult,
        metadata: dict[str, Any] | None = None,
    ) -> RawSearchBundle:
        return RawSearchBundle(
            run_id=context.run_id,
            agent_type=self.agent_type,
            executed_at=utc_now_iso(),
            queries=queries,
            raw_findings=raw_findings,
            local_validation={
                "passed": validation.passed,
                "summary": validation.summary,
                "warnings": validation.warnings,
            },
            metadata=metadata or {},
        )

    def run(self, context: SearchExecutionContext) -> RawSearchBundle:
        queries = self.build_queries(context)
        raw_findings = self.search(queries, context)
        validation = self.local_validate(raw_findings)
        return self.to_raw_bundle(context=context, queries=queries, raw_findings=raw_findings, validation=validation)
