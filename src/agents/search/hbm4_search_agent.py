"""HBM4 search agent."""

from __future__ import annotations

from src.agents.base.base_search_agent import BaseSearchAgent


class HBM4SearchAgent(BaseSearchAgent):
    agent_type = "hbm4"
    technology = "HBM4"
    focus_terms = ["roadmap", "performance", "mass production timing"]

