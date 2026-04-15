"""Runtime settings for supervisor orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class SupervisorSettings:
    max_retry_count: int = 2
    allow_unresolved_after_retry_limit: bool = True
    allow_analysis_on_warning: bool = True
    require_reference_trace_for_report: bool = True
    final_approval_allow_warning_status: bool = True
    final_approval_max_warning_count: int = 50
    final_approval_blocking_warning_codes: tuple[str, ...] = ("UNRESOLVED_CELL", "MISSING_EVIDENCE")
    require_report_sections: tuple[str, ...] = (
        "summary",
        "background",
        "technology_status",
        "competitor_trends",
        "strategic_implications",
        "reference",
    )
    default_output_format: str = "pdf"
    default_technology_axes: tuple[str, ...] = (
        "HBM4",
        "PIM",
        "CXL",
        "Advanced Packaging",
        "Thermal·Power",
    )
    default_seed_competitors: tuple[str, ...] = ("SK hynix", "Micron")
    metadata_defaults: dict[str, object] = field(
        default_factory=lambda: {"raw_content_policy": "preserve", "key_points_policy": "separate"}
    )
