"""Thermal and power management search agent."""

from __future__ import annotations

from src.agents.base.base_search_agent import BaseSearchAgent


class ThermalPowerSearchAgent(BaseSearchAgent):
    agent_type = "thermal_power"
    technology = "Thermal·Power"
    focus_terms = ["cooling", "power delivery", "system efficiency"]
