"""Deterministic rule-based judge used when a hosted LLM is unavailable."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .base_llm_provider import BaseLLMProvider, LLMResponse


@dataclass(slots=True)
class JudgeAssessment:
    score: int
    rationale: str
    tags: list[str]


class RuleBasedLLMJudgeProvider(BaseLLMProvider):
    def generate_text(self, prompt: str, *, system_prompt: str | None = None) -> LLMResponse:
        assessment = self.judge_text(prompt)
        return LLMResponse(
            text=f"score={assessment.score}; rationale={assessment.rationale}",
            metadata={"tags": assessment.tags, "system_prompt": system_prompt},
        )

    def judge_text(self, text: str) -> JudgeAssessment:
        normalized = " ".join(text.lower().split())
        tags: list[str] = []
        score = 3
        if any(token in normalized for token in ("mass production", "volume shipment", "deployment", "qualified")):
            score = 5
            tags.append("direct_execution")
        elif any(token in normalized for token in ("prototype", "pilot", "sample", "poC", "proof of concept")):
            score = 4
            tags.append("validation")
        elif any(token in normalized for token in ("patent", "job", "hiring", "conference", "paper")):
            score = 2
            tags.append("indirect_signal")
        rationale = "Rule-based LLM judge inferred a deterministic score from execution language."
        return JudgeAssessment(score=score, rationale=rationale, tags=tags)

    def summarize_conflict(self, *, has_conflict: bool, conflict_type: str | None, rationale: str) -> str:
        if not has_conflict:
            return "No internal conflict detected."
        return f"Conflict candidate ({conflict_type}): {rationale}"

