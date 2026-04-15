from pathlib import Path

from src.app.bootstrap import build_app, build_llm_provider, build_search_provider
from src.config.app_settings import AppSettings
from src.providers.embedding.jina_embedding_provider import JinaEmbeddingProvider
from src.providers.embedding.noop_embedding_provider import NoopEmbeddingProvider
from src.providers.llm.llm_judge_provider import RuleBasedLLMJudgeProvider
from src.providers.llm.openai_llm_provider import OpenAILLMProvider
from src.providers.search.deterministic_search_provider import DeterministicSearchProvider
from src.providers.search.tavily_search_provider import TavilySearchProvider


def test_app_settings_loads_from_dotenv(tmp_path: Path):
    dotenv = tmp_path / ".env"
    dotenv.write_text(
        "\n".join(
            [
                "SEARCH_PROVIDER=tavily",
                "LLM_PROVIDER=openai",
                "OPENAI_API_KEY=test-openai",
                "OPENAI_MODEL=gpt-test",
                "TAVILY_API_KEY=test-tavily",
            ]
        ),
        encoding="utf-8",
    )

    app = build_app(dotenv_path=str(dotenv))

    assert app.app_settings.search_provider == "tavily"
    assert app.app_settings.llm_provider == "openai"
    assert app.app_settings.openai_model == "gpt-test"


def test_build_search_provider_uses_tavily_when_key_present():
    settings = AppSettings(search_provider="tavily", tavily_api_key="key")
    provider = build_search_provider(settings)
    assert isinstance(provider, TavilySearchProvider)


def test_build_search_provider_falls_back_to_deterministic():
    settings = AppSettings(search_provider="tavily", tavily_api_key="")
    provider = build_search_provider(settings)
    assert isinstance(provider, DeterministicSearchProvider)


def test_build_llm_provider_uses_openai_when_key_present():
    settings = AppSettings(llm_provider="openai", openai_api_key="key", openai_model="gpt-test")
    provider = build_llm_provider(settings)
    assert isinstance(provider, OpenAILLMProvider)
    assert provider.model == "gpt-test"


def test_build_llm_provider_falls_back_to_rule_based():
    settings = AppSettings(llm_provider="openai", openai_api_key="")
    provider = build_llm_provider(settings)
    assert isinstance(provider, RuleBasedLLMJudgeProvider)


def test_build_embedding_provider_uses_jina_when_key_present():
    from src.app.bootstrap import build_embedding_provider

    settings = AppSettings(embedding_provider="jina", jina_api_key="key", embedding_model="jina-embeddings-v4")
    provider = build_embedding_provider(settings)
    assert isinstance(provider, JinaEmbeddingProvider)
    assert provider.model == "jina-embeddings-v4"


def test_build_embedding_provider_falls_back_to_noop():
    from src.app.bootstrap import build_embedding_provider

    settings = AppSettings(embedding_provider="jina", jina_api_key="")
    provider = build_embedding_provider(settings)
    assert isinstance(provider, NoopEmbeddingProvider)
