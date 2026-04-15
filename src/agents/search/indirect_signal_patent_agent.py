"""Indirect signal and patent search agent."""

from __future__ import annotations

from src.agents.base.base_search_agent import BaseSearchAgent


class IndirectSignalPatentSearchAgent(BaseSearchAgent):
    agent_type = "indirect_signal"
    technology = "Indirect Signal"
    focus_terms = ["patent", "job posting", "conference presentation"]

