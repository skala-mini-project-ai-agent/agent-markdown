"""Offline deterministic search provider used for scaffolding and tests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.providers.search.base_search_provider import BaseSearchProvider
from src.schemas.raw_result_schema import RawFinding, SearchQuery, utc_now_iso


@dataclass(slots=True)
class DeterministicSearchProvider(BaseSearchProvider):
    default_source_name: str = "Deterministic Search Corpus"

    def search(
        self,
        query: SearchQuery,
        *,
        run_id: str,
        agent_type: str,
        context: dict[str, Any] | None = None,
    ) -> list[RawFinding]:
        context = context or {}
        technology = query.technology or context.get("technology", "")
        base_companies = context.get("seed_competitors") or ["SK hynix", "Micron"]
        freshness_year = context.get("freshness_start_year", 2024)
        primary_company = base_companies[0]
        secondary_company = base_companies[1] if len(base_companies) > 1 else primary_company
        generated_at = utc_now_iso()

        results: list[RawFinding] = []
        for index in range(2):
            company = [primary_company] if index == 0 else [secondary_company]
            source_type = "press_release" if index == 0 else "news"
            signal_type = "direct" if index == 0 else "indirect"
            title = f"{technology or agent_type} signal for {query.query} #{index + 1}"
            content = (
                f"{title}\n"
                f"Source focuses on {technology or agent_type}.\n"
                f"Company signal: {company[0]}.\n"
                f"Freshness floor: {freshness_year}.\n"
                f"Follow-up indicates execution and roadmap implications."
            )
            results.append(
                RawFinding(
                    raw_finding_id=f"{run_id}:{agent_type}:{index + 1}",
                    run_id=run_id,
                    agent_type=agent_type,
                    query=query.query,
                    title=title,
                    source_type=source_type,
                    signal_type=signal_type,
                    source_name=self.default_source_name,
                    published_at=f"{freshness_year}-06-15T00:00:00Z",
                    url=f"https://example.invalid/{agent_type}/{index + 1}",
                    raw_content=content,
                    key_points=[
                        f"{technology or agent_type} execution update",
                        f"{company[0]} roadmap implication",
                    ],
                    company=company,
                    technology=technology or agent_type,
                    signals=[
                        f"{agent_type}_signal",
                        f"{technology or agent_type}_trend",
                    ],
                    counter_signals=["validation_gap"] if index == 1 else [],
                    confidence="high" if index == 0 else "medium",
                    metadata={
                        "query_metadata": query.metadata,
                        "generated_at": generated_at,
                    },
                )
            )
        return results

