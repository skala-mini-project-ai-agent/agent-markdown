"""CXL search agent."""

from __future__ import annotations

from src.agents.base.base_search_agent import BaseSearchAgent


class CXLSearchAgent(BaseSearchAgent):
    agent_type = "cxl"
    technology = "CXL"
    focus_terms = ["memory expansion", "ecosystem", "standard adoption"]

