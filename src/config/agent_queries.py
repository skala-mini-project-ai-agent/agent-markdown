"""Query planning hints keyed by search agent type."""

from __future__ import annotations


AGENT_QUERY_TERMS: dict[str, tuple[str, ...]] = {
    "pim": ("architecture", "productization", "customer collaboration"),
    "cxl": ("memory expansion", "ecosystem", "standard adoption"),
    "hbm4": ("roadmap", "performance", "mass production timing"),
    "packaging": ("hybrid bonding", "interposer", "UCIe"),
    "thermal_power": ("cooling", "power delivery", "thermal bottleneck"),
    "indirect_signal": ("patent", "job posting", "conference presentation"),
}
