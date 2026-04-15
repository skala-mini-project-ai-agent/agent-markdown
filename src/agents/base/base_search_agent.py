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
        retry_hints = self._retry_hints(context)
        source_hints = self._source_hints_for_retry(retry_hints)
        if terms:
            for term in terms[:3]:
                queries.append(
                    SearchQuery(
                        query=self._compose_query(context, term, retry_hints),
                        technology=self.technology,
                        source_hints=source_hints,
                        metadata={
                            "term": term,
                            "agent_type": self.agent_type,
                            "retry_hints": retry_hints,
                            "retry_attempt": context.metadata.get("retry_attempt", 0),
                        },
                    )
                )
        else:
            queries.append(
                SearchQuery(
                    query=self._compose_query(context, None, retry_hints),
                    technology=self.technology,
                    source_hints=source_hints,
                    metadata={
                        "agent_type": self.agent_type,
                        "retry_hints": retry_hints,
                        "retry_attempt": context.metadata.get("retry_attempt", 0),
                    },
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
        self._propagate_validation(raw_findings, validation)
        return self.to_raw_bundle(context=context, queries=queries, raw_findings=raw_findings, validation=validation)

    def _retry_hints(self, context: SearchExecutionContext) -> list[dict[str, Any]]:
        retry_plan = context.metadata.get("retry_plan", {})
        retry_targets = retry_plan.get("retry_targets", []) if isinstance(retry_plan, dict) else []
        return [target for target in retry_targets if target.get("agent") == self.agent_type]

    def _compose_query(
        self,
        context: SearchExecutionContext,
        term: str | None,
        retry_hints: list[dict[str, Any]],
    ) -> str:
        base = f"{context.user_query or self.technology} {term or ''}".strip()
        if not retry_hints:
            return base
        retry_terms: list[str] = []
        for hint in retry_hints:
            reason = str(hint.get("reason", ""))
            if reason == "low_confidence":
                retry_terms.append("validated benchmark customer qualification")
            elif "conflict" in reason:
                retry_terms.append("independent confirmation rebuttal evidence")
            elif "bias" in reason:
                retry_terms.append("independent analyst paper standards consortium")
            else:
                retry_terms.append("additional evidence cross source verification")
            retry_terms.extend(str(term) for term in hint.get("expansion_terms", []))
        suffix = " ".join(dict.fromkeys(retry_terms))
        return f"{base} {suffix}".strip()

    def _source_hints_for_retry(self, retry_hints: list[dict[str, Any]]) -> list[str]:
        hints = ["news", "press_release", "paper"]
        reasons = {str(hint.get("reason", "")) for hint in retry_hints}
        if any("conflict" in reason for reason in reasons):
            hints.extend(["paper", "filing"])
        if "company_bias" in reasons:
            hints.extend(["conference", "patent"])
        if "low_confidence" in reasons:
            hints.extend(["paper", "conference"])
        return list(dict.fromkeys(hints))

    def _propagate_validation(
        self,
        raw_findings: list[RawFinding],
        validation: AgentValidationResult,
    ) -> None:
        urls = [finding.url for finding in raw_findings if finding.url]
        duplicate_urls = {url for url, count in Counter(urls).items() if count > 1}
        for finding in raw_findings:
            missing_fields = []
            if not finding.title:
                missing_fields.append("title")
            if not finding.url:
                missing_fields.append("url")
            if not finding.published_at:
                missing_fields.append("published_at")
            if not finding.raw_content:
                missing_fields.append("raw_content")
            finding.local_validation = {
                "passed": validation.passed and not missing_fields and finding.url not in duplicate_urls,
                "bundle_passed": validation.passed,
                "bundle_warnings": list(validation.warnings),
                "missing_fields": missing_fields,
                "duplicate_url": finding.url in duplicate_urls if finding.url else False,
                "source_name_present": bool(finding.source_name),
            }
