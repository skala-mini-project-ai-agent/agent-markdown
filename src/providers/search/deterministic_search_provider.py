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
        retry_attempt = int((query.metadata or {}).get("retry_attempt", 0))
        retry_hints = list((query.metadata or {}).get("retry_hints", []))
        evidence_profile = self._build_evidence_profile(query.source_hints, retry_hints, retry_attempt)

        results: list[RawFinding] = []
        companies = [primary_company, secondary_company]
        for index, profile in enumerate(evidence_profile):
            company = [companies[index % len(companies)]]
            source_type = profile["source_type"]
            source_name = profile["source_name"]
            signal_type = profile["signal_type"]
            title = f"{technology or agent_type} signal for {query.query} #{index + 1}"
            content = (
                f"{title}\n"
                f"Source focuses on {technology or agent_type}.\n"
                f"Company signal: {company[0]}.\n"
                f"Freshness floor: {freshness_year}.\n"
                f"Follow-up indicates execution and roadmap implications.\n"
                f"Evidence posture: {profile['evidence_phrase']}."
            )
            results.append(
                RawFinding(
                    raw_finding_id=f"{run_id}:{agent_type}:{query.metadata.get('term', 'base')}:{retry_attempt}:{index + 1}",
                    run_id=run_id,
                    agent_type=agent_type,
                    query=query.query,
                    title=title,
                    source_type=source_type,
                    signal_type=signal_type,
                    source_name=source_name,
                    published_at=f"{freshness_year + min(retry_attempt, 1)}-0{(index % 6) + 1}-15T00:00:00Z",
                    url=f"https://example.invalid/{agent_type}/{query.metadata.get('term', 'base')}/{retry_attempt}/{index + 1}",
                    raw_content=content,
                    key_points=[
                        f"{technology or agent_type} execution update",
                        f"{company[0]} roadmap implication",
                        profile["evidence_phrase"],
                    ],
                    company=company,
                    technology=technology or agent_type,
                    signals=[
                        f"{agent_type}_signal",
                        f"{technology or agent_type}_trend",
                        profile["signal_label"],
                    ],
                    counter_signals=list(profile["counter_signals"]),
                    confidence=profile["confidence"],
                    metadata={
                        "query_metadata": query.metadata,
                        "generated_at": generated_at,
                        "retry_attempt": retry_attempt,
                        "profile": profile["profile_name"],
                    },
                )
            )
        return results

    def _build_evidence_profile(
        self,
        source_hints: list[str],
        retry_hints: list[dict[str, Any]],
        retry_attempt: int,
    ) -> list[dict[str, Any]]:
        preferred_types = list(dict.fromkeys(source_hints or ["news", "paper", "conference", "filing"]))
        source_names = {
            "news": "Global Tech News",
            "press_release": "Company Newsroom",
            "paper": "IEEE Journal",
            "conference": "Hot Chips",
            "filing": "Regulatory Filing Watch",
            "patent": "Patent Monitor",
        }
        quality_boost = retry_attempt > 0
        reasons = {str(hint.get("reason", "")) for hint in retry_hints}
        profiles: list[dict[str, Any]] = []
        for index, source_type in enumerate(preferred_types[:4]):
            direct_signal = index % 2 == 0 or quality_boost
            confidence = "high" if quality_boost or source_type in {"paper", "filing"} else "medium"
            counter_signals: list[str] = []
            if "counter_signals_present" in reasons and source_type in {"paper", "filing"} and retry_attempt == 0:
                counter_signals = ["independent_rebuttal_needed"]
            profiles.append(
                {
                    "profile_name": f"profile_{index}",
                    "source_type": source_type,
                    "source_name": source_names.get(source_type, self.default_source_name),
                    "signal_type": "direct" if direct_signal else "indirect",
                    "confidence": confidence,
                    "counter_signals": counter_signals if retry_attempt == 0 else [],
                    "evidence_phrase": self._evidence_phrase(source_type, quality_boost, reasons),
                    "signal_label": f"{source_type}_validated_signal",
                }
            )
        if len(profiles) < 4:
            while len(profiles) < 4:
                profiles.append(
                    {
                        "profile_name": f"profile_{len(profiles)}",
                        "source_type": "paper",
                        "source_name": "IEEE Journal",
                        "signal_type": "direct",
                        "confidence": "high",
                        "counter_signals": [],
                        "evidence_phrase": "independent validation update",
                        "signal_label": "paper_validated_signal",
                    }
                )
        return profiles

    def _evidence_phrase(self, source_type: str, quality_boost: bool, reasons: set[str]) -> str:
        if quality_boost and "low_confidence" in reasons:
            return "customer qualification and benchmark validation"
        if quality_boost and "company_bias" in reasons:
            return "third-party analyst and consortium confirmation"
        if quality_boost and any("conflict" in reason for reason in reasons):
            return "independent rebuttal and cross-source confirmation"
        phrases = {
            "news": "ecosystem adoption and deployment progress",
            "press_release": "product roadmap and customer qualification update",
            "paper": "lab validation and technical benchmark result",
            "conference": "conference demonstration and interoperability signal",
            "filing": "commercial deployment and supply commitment",
            "patent": "patent activity and capability expansion signal",
        }
        return phrases.get(source_type, "technology execution signal")
