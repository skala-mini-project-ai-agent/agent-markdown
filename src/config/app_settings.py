"""Application settings loaded from environment and .env."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _parse_dotenv(path: str | Path = ".env") -> dict[str, str]:
    env_path = Path(path)
    if not env_path.exists():
        return {}
    values: dict[str, str] = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _env_value(key: str, dotenv: dict[str, str], default: str = "") -> str:
    return os.getenv(key, dotenv.get(key, default))


def _env_bool(key: str, dotenv: dict[str, str], default: bool = False) -> bool:
    value = _env_value(key, dotenv, "true" if default else "false").lower()
    return value in {"1", "true", "yes", "on"}


def _env_int(key: str, dotenv: dict[str, str], default: int) -> int:
    try:
        return int(_env_value(key, dotenv, str(default)))
    except ValueError:
        return default


@dataclass(frozen=True, slots=True)
class AppSettings:
    search_provider: str = "deterministic"
    llm_provider: str = "rule_based"
    embedding_provider: str = "none"
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"
    tavily_api_key: str = ""
    tavily_max_results: int = 5
    langchain_api_key: str = ""
    langchain_tracing_v2: bool = False
    langchain_endpoint: str = ""
    langchain_project: str = ""
    huggingfacehub_api_token: str = ""
    jina_api_key: str = ""
    embedding_model: str = "jina-embeddings-v4"

    @classmethod
    def load(cls, *, dotenv_path: str | Path = ".env") -> "AppSettings":
        dotenv = _parse_dotenv(dotenv_path)
        return cls(
            search_provider=_env_value("SEARCH_PROVIDER", dotenv, "deterministic"),
            llm_provider=_env_value("LLM_PROVIDER", dotenv, "rule_based"),
            embedding_provider=_env_value("EMBEDDING_PROVIDER", dotenv, "none"),
            openai_api_key=_env_value("OPENAI_API_KEY", dotenv),
            openai_model=_env_value("OPENAI_MODEL", dotenv, "gpt-4.1-mini"),
            tavily_api_key=_env_value("TAVILY_API_KEY", dotenv),
            tavily_max_results=_env_int("TAVILY_MAX_RESULTS", dotenv, 5),
            langchain_api_key=_env_value("LANGCHAIN_API_KEY", dotenv),
            langchain_tracing_v2=_env_bool("LANGCHAIN_TRACING_V2", dotenv, False),
            langchain_endpoint=_env_value("LANGCHAIN_ENDPOINT", dotenv),
            langchain_project=_env_value("LANGCHAIN_PROJECT", dotenv),
            huggingfacehub_api_token=_env_value("HUGGINGFACEHUB_API_TOKEN", dotenv),
            jina_api_key=_env_value("JINA_API_KEY", dotenv),
            embedding_model=_env_value("EMBEDDING_MODEL", dotenv, "jina-embeddings-v4"),
        )
