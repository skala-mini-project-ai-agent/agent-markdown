"""Key point extraction from raw content."""

from __future__ import annotations

import re

from src.schemas.raw_result_schema import RawFinding


def extract_key_points(raw_finding: RawFinding) -> list[str]:
    if raw_finding.key_points:
        return [point.strip() for point in raw_finding.key_points if point.strip()]
    text = raw_finding.raw_content.strip()
    if not text:
        return []
    segments = re.split(r"[\n;]+|(?<=[.!?])\s+", text)
    points = [segment.strip(" -•\t") for segment in segments if segment.strip(" -•\t")]
    return points[:5]

