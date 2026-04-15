from src.providers.embedding.jina_embedding_provider import JinaEmbeddingProvider


def test_jina_provider_maps_generic_retrieval_to_passage():
    provider = JinaEmbeddingProvider(api_key="key")
    assert provider._resolve_task("retrieval") == "retrieval.passage"


def test_jina_provider_preserves_query_task():
    provider = JinaEmbeddingProvider(api_key="key")
    assert provider._resolve_task("retrieval.query") == "retrieval.query"


def test_jina_provider_sanitizes_long_text():
    provider = JinaEmbeddingProvider(api_key="key", max_chars=20)
    text = "a" * 40
    sanitized = provider._sanitize_text(text)
    assert "..." in sanitized
    assert len(sanitized) <= 25
