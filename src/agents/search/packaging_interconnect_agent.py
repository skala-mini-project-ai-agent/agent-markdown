"""Advanced packaging and interconnect search agent."""

from __future__ import annotations

from src.agents.base.base_search_agent import BaseSearchAgent


class PackagingInterconnectSearchAgent(BaseSearchAgent):
    agent_type = "packaging"
    technology = "Advanced Packaging"
    focus_terms = ["2.5D packaging", "3D packaging", "hybrid bonding"]

