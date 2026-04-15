"""Tagging helpers for normalized evidence."""

from __future__ import annotations

from typing import Any

from src.schemas.raw_result_schema import RawFinding


def infer_technology(raw_finding: RawFinding) -> str:
    if raw_finding.technology:
        return raw_finding.technology
    if raw_finding.agent_type == "packaging":
        return "Advanced Packaging"
    if raw_finding.agent_type == "thermal_power":
        return "Thermal·Power"
    if raw_finding.agent_type == "indirect_signal":
        return "Indirect Signal"
    return raw_finding.agent_type.upper()


def infer_company(raw_finding: RawFinding) -> list[str]:
    if raw_finding.company:
        return [str(company) for company in raw_finding.company if str(company)]
    return []


def infer_source_type(raw_finding: RawFinding) -> str:
    return raw_finding.source_type or "other"


def build_metadata(raw_finding: RawFinding) -> dict[str, Any]:
    return {
        "agent_type": raw_finding.agent_type,
        "query": raw_finding.query,
        "raw_finding_id": raw_finding.raw_finding_id,
        **dict(raw_finding.metadata),
    }
