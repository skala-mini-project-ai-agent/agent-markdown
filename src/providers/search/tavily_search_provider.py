"""Tavily-backed search provider for live search integration."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from time import sleep
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from src.normalization.tagging import extract_companies_from_text
from src.providers.search.base_search_provider import BaseSearchProvider
from src.providers.search.deterministic_search_provider import DeterministicSearchProvider
from src.schemas.raw_result_schema import RawFinding, SearchQuery, utc_now_iso


@dataclass(slots=True)
class TavilySearchProvider(BaseSearchProvider):
    api_key: str
    max_results: int = 5
    endpoint: str = "https://api.tavily.com/search"
    max_retries: int = 2
    backoff_seconds: float = 0.5
    cache_dir: str | Path = "data/cache/tavily"
    fallback_provider: BaseSearchProvider | None = None

    def search(
        self,
        query: SearchQuery,
        *,
        run_id: str,
        agent_type: str,
        context: dict[str, Any] | None = None,
    ) -> list[RawFinding]:
        if self.fallback_provider is None:
            self.fallback_provider = DeterministicSearchProvider()
        payload = {
            "api_key": self.api_key,
            "query": query.query,
            "max_results": self.max_results,
            "search_depth": "advanced",
            "include_answer": False,
            "include_raw_content": True,
        }
        technology = query.technology or (context or {}).get("technology", "")
        seed_competitors = [str(item) for item in (context or {}).get("seed_competitors", []) if str(item)]
        cached_items = self._load_cached_items(query, agent_type=agent_type)
        last_error: Exception | None = None

        for attempt in range(self.max_retries + 1):
            request = Request(
                self.endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={"content-type": "application/json", "accept": "application/json", "user-agent": "curl/8.7.1"},
                method="POST",
            )
            try:
                with urlopen(request, timeout=30) as response:
                    data = json.loads(response.read().decode("utf-8"))
                items = list(data.get("results", []))
                if items:
                    self._save_cached_items(query, agent_type=agent_type, items=items)
                return self._build_findings(
                    items,
                    query=query,
                    run_id=run_id,
                    agent_type=agent_type,
                    technology=technology,
                    seed_competitors=seed_competitors,
                    metadata_extra={"cache_status": "live"},
                )
            except HTTPError as exc:  # pragma: no cover - network path
                last_error = exc
                if exc.code in {429, 430, 431, 432} and attempt < self.max_retries:
                    sleep(self.backoff_seconds * (attempt + 1))
                    continue
                break
            except URLError as exc:  # pragma: no cover - network path
                last_error = exc
                if attempt < self.max_retries:
                    sleep(self.backoff_seconds * (attempt + 1))
                    continue
                break

        if cached_items:
            return self._build_findings(
                cached_items,
                query=query,
                run_id=run_id,
                agent_type=agent_type,
                technology=technology,
                seed_competitors=seed_competitors,
                metadata_extra={"cache_status": "cached"},
            )

        if self.fallback_provider is not None:
            findings = self.fallback_provider.search(
                query,
                run_id=run_id,
                agent_type=agent_type,
                context=context,
            )
            for finding in findings:
                finding.metadata["cache_status"] = "fallback"
                finding.metadata["fallback_provider"] = type(self.fallback_provider).__name__
            return findings

        raise RuntimeError(f"Tavily search failed: {last_error}")

    def _build_findings(
        self,
        items: list[dict[str, Any]],
        *,
        query: SearchQuery,
        run_id: str,
        agent_type: str,
        technology: str,
        seed_competitors: list[str],
        metadata_extra: dict[str, Any] | None = None,
    ) -> list[RawFinding]:
        results: list[RawFinding] = []
        metadata_extra = metadata_extra or {}
        for index, item in enumerate(items, start=1):
            content = str(item.get("raw_content") or item.get("content") or "")
            title = str(item.get("title") or f"{technology} search result {index}")
            source_name = str(item.get("site_name") or "Tavily")
            url = str(item.get("url") or "")
            company = extract_companies_from_text(
                "\n".join(filter(None, [title, content, source_name, url, query.query])),
                candidates=seed_competitors,
            )
            results.append(
                RawFinding(
                    raw_finding_id=f"{run_id}:{agent_type}:{index}",
                    run_id=run_id,
                    agent_type=agent_type,
                    query=query.query,
                    title=title,
                    source_type="news",
                    signal_type="direct",
                    source_name=source_name,
                    published_at=str(item.get("published_date") or utc_now_iso()),
                    url=url,
                    raw_content=content,
                    company=company,
                    technology=technology,
                    confidence="medium",
                    metadata={
                        "query_metadata": query.metadata,
                        "score": item.get("score"),
                        "site_name": source_name,
                        "seed_competitors": seed_competitors,
                        **metadata_extra,
                    },
                )
            )
        return results

    def _cache_path(self, query: SearchQuery, *, agent_type: str) -> Path:
        base = Path(self.cache_dir)
        digest = hashlib.sha256(f"{agent_type}:{query.technology}:{query.query}".encode("utf-8")).hexdigest()[:16]
        return base / f"{digest}.json"

    def _load_cached_items(self, query: SearchQuery, *, agent_type: str) -> list[dict[str, Any]]:
        path = self._cache_path(query, agent_type=agent_type)
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
        return list(data.get("results", []))

    def _save_cached_items(self, query: SearchQuery, *, agent_type: str, items: list[dict[str, Any]]) -> None:
        path = self._cache_path(query, agent_type=agent_type)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"agent_type": agent_type, "technology": query.technology, "query": query.query, "results": items}
        path.write_text(json.dumps(payload, ensure_ascii=True), encoding="utf-8")
