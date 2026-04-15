"""PIM search agent."""

from __future__ import annotations

from src.agents.base.base_search_agent import BaseSearchAgent


class PIMSearchAgent(BaseSearchAgent):
    agent_type = "pim"
    technology = "PIM"
    focus_terms = ["architecture", "productization", "customer collaboration"]

