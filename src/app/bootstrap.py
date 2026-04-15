"""Bootstrap helpers for assembling providers and the supervisor from settings."""

from __future__ import annotations

from dataclasses import dataclass

from ..agents.analysis.report_generation_agent import ReportGenerationAgent
from ..agents.analysis.threat_analysis_agent import ThreatAnalysisAgent
from ..agents.analysis.trl_analysis_agent import TRLAnalysisAgent
from ..config.app_settings import AppSettings
from ..config.settings import SupervisorSettings
from ..orchestration.parallel_search_runner import ParallelSearchRunner
from ..providers.embedding.base_embedding_provider import BaseEmbeddingProvider
from ..providers.embedding.jina_embedding_provider import JinaEmbeddingProvider
from ..providers.embedding.noop_embedding_provider import NoopEmbeddingProvider
from ..providers.llm.base_llm_provider import BaseLLMProvider
from ..providers.llm.llm_judge_provider import RuleBasedLLMJudgeProvider
from ..providers.llm.openai_llm_provider import OpenAILLMProvider
from ..providers.search.base_search_provider import BaseSearchProvider
from ..providers.search.deterministic_search_provider import DeterministicSearchProvider
from ..providers.search.tavily_search_provider import TavilySearchProvider
from ..supervisor.supervisor import CentralSupervisor


@dataclass(slots=True)
class AppContainer:
    app_settings: AppSettings
    supervisor_settings: SupervisorSettings
    search_provider: BaseSearchProvider
    llm_provider: BaseLLMProvider
    embedding_provider: BaseEmbeddingProvider
    search_runner: ParallelSearchRunner
    trl_agent: TRLAnalysisAgent
    threat_agent: ThreatAnalysisAgent
    report_agent: ReportGenerationAgent
    supervisor: CentralSupervisor


def build_search_provider(settings: AppSettings) -> BaseSearchProvider:
    provider_name = settings.search_provider.lower()
    if provider_name == "tavily" and settings.tavily_api_key:
        return TavilySearchProvider(
            api_key=settings.tavily_api_key,
            max_results=settings.tavily_max_results,
            fallback_provider=DeterministicSearchProvider(),
        )
    return DeterministicSearchProvider()


def build_llm_provider(settings: AppSettings) -> BaseLLMProvider:
    provider_name = settings.llm_provider.lower()
    if provider_name == "openai" and settings.openai_api_key:
        return OpenAILLMProvider(api_key=settings.openai_api_key, model=settings.openai_model)
    return RuleBasedLLMJudgeProvider()


def build_embedding_provider(settings: AppSettings) -> BaseEmbeddingProvider:
    provider_name = settings.embedding_provider.lower()
    if provider_name == "jina" and settings.jina_api_key:
        return JinaEmbeddingProvider(api_key=settings.jina_api_key, model=settings.embedding_model)
    return NoopEmbeddingProvider()


def build_app(*, dotenv_path: str = ".env") -> AppContainer:
    app_settings = AppSettings.load(dotenv_path=dotenv_path)
    supervisor_settings = SupervisorSettings()

    search_provider = build_search_provider(app_settings)
    llm_provider = build_llm_provider(app_settings)
    embedding_provider = build_embedding_provider(app_settings)

    search_runner = ParallelSearchRunner(provider=search_provider, embedding_provider=embedding_provider)
    trl_agent = TRLAnalysisAgent(llm_provider=llm_provider)
    threat_agent = ThreatAnalysisAgent(llm_provider=llm_provider)
    report_agent = ReportGenerationAgent(embedding_provider=embedding_provider)
    supervisor = CentralSupervisor(
        settings=supervisor_settings,
        search_runner=search_runner,
        trl_agent=trl_agent,
        threat_agent=threat_agent,
        report_agent=report_agent,
        embedding_provider=embedding_provider,
    )

    return AppContainer(
        app_settings=app_settings,
        supervisor_settings=supervisor_settings,
        search_provider=search_provider,
        llm_provider=llm_provider,
        embedding_provider=embedding_provider,
        search_runner=search_runner,
        trl_agent=trl_agent,
        threat_agent=threat_agent,
        report_agent=report_agent,
        supervisor=supervisor,
    )
