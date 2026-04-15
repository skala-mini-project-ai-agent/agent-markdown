import json
from pathlib import Path
from urllib.error import HTTPError

from src.providers.search.deterministic_search_provider import DeterministicSearchProvider
from src.providers.search.tavily_search_provider import TavilySearchProvider
from src.schemas.raw_result_schema import SearchQuery


class _Response:
    def __init__(self, payload: dict):
        self.payload = payload

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_tavily_provider_uses_cache_on_http_error(tmp_path: Path, monkeypatch):
    provider = TavilySearchProvider(
        api_key="key",
        cache_dir=tmp_path / "cache",
        fallback_provider=DeterministicSearchProvider(),
        max_retries=0,
    )
    query = SearchQuery(query="HBM4 Micron roadmap", technology="HBM4")
    cache_path = provider._cache_path(query, agent_type="hbm4")
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps(
            {
                "results": [
                    {
                        "title": "Micron HBM4 roadmap",
                        "url": "https://example.com/micron",
                        "raw_content": "Micron discusses HBM4 progress.",
                        "site_name": "Example",
                        "published_date": "2026-04-15T00:00:00+00:00",
                        "score": 0.9,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    def _raise(*args, **kwargs):
        raise HTTPError("https://api.tavily.com/search", 432, "blocked", hdrs=None, fp=None)

    monkeypatch.setattr("src.providers.search.tavily_search_provider.urlopen", _raise)
    findings = provider.search(
        query,
        run_id="run-1",
        agent_type="hbm4",
        context={"seed_competitors": ["Micron", "Samsung"]},
    )

    assert len(findings) == 1
    assert findings[0].metadata["cache_status"] == "cached"
    assert findings[0].company == ["Micron"]


def test_tavily_provider_falls_back_when_no_cache(tmp_path: Path, monkeypatch):
    provider = TavilySearchProvider(
        api_key="key",
        cache_dir=tmp_path / "cache",
        fallback_provider=DeterministicSearchProvider(),
        max_retries=0,
    )
    query = SearchQuery(query="HBM4 Micron roadmap", technology="HBM4")

    def _raise(*args, **kwargs):
        raise HTTPError("https://api.tavily.com/search", 432, "blocked", hdrs=None, fp=None)

    monkeypatch.setattr("src.providers.search.tavily_search_provider.urlopen", _raise)
    findings = provider.search(
        query,
        run_id="run-2",
        agent_type="hbm4",
        context={"seed_competitors": ["Micron", "Samsung"]},
    )

    assert findings
    assert findings[0].metadata["cache_status"] == "fallback"
    assert findings[0].metadata["fallback_provider"] == "DeterministicSearchProvider"


def test_tavily_provider_saves_cache_on_success(tmp_path: Path, monkeypatch):
    provider = TavilySearchProvider(api_key="key", cache_dir=tmp_path / "cache", max_retries=0)
    query = SearchQuery(query="HBM4 Micron roadmap", technology="HBM4")

    def _success(*args, **kwargs):
        return _Response(
            {
                "results": [
                    {
                        "title": "Micron HBM4 roadmap",
                        "url": "https://example.com/micron",
                        "raw_content": "Micron discusses HBM4 progress.",
                        "site_name": "Example",
                        "published_date": "2026-04-15T00:00:00+00:00",
                        "score": 0.9,
                    }
                ]
            }
        )

    monkeypatch.setattr("src.providers.search.tavily_search_provider.urlopen", _success)
    findings = provider.search(
        query,
        run_id="run-3",
        agent_type="hbm4",
        context={"seed_competitors": ["Micron", "Samsung"]},
    )

    assert len(findings) == 1
    assert findings[0].metadata["cache_status"] == "live"
    assert provider._cache_path(query, agent_type="hbm4").exists()
