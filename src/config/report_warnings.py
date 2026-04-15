"""Warning codes and messages for the report generation stage."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WarningTemplate:
    code: str
    message_template: str


# Warning codes emitted by ReportGenerationAgent.
UNRESOLVED_CELL = WarningTemplate(
    code="UNRESOLVED_CELL",
    message_template="분석이 미완료된 셀({cells})이 존재합니다. 해당 항목은 불확실성이 높으며 재검토가 필요합니다.",
)

CONFLICT_FLAG = WarningTemplate(
    code="CONFLICT_FLAG",
    message_template="TRL과 위협 수준 간 상충이 감지된 셀({cells})이 존재합니다. 해당 항목의 판단에 주의가 필요합니다.",
)

LOW_CONFIDENCE = WarningTemplate(
    code="LOW_CONFIDENCE",
    message_template="신뢰도가 낮은 분석 셀({cells})이 존재합니다. 추가 증거 수집을 권장합니다.",
)

TRL_THREAT_DIVERGENCE = WarningTemplate(
    code="TRL_THREAT_DIVERGENCE",
    message_template=(
        "TRL 수준과 위협 수준 간 유의미한 괴리가 감지된 셀({cells})이 있습니다. "
        "보고서 내 '기술 현황' 및 '경쟁사 동향' 섹션에서 배경 분석을 확인하십시오."
    ),
)

MISSING_EVIDENCE = WarningTemplate(
    code="MISSING_EVIDENCE",
    message_template="일부 주장({cells})에 대한 evidence trace가 누락되었습니다.",
)


def format_warning(template: WarningTemplate, cells: list[str]) -> str:
    cell_str = ", ".join(cells) if cells else "-"
    return template.message_template.format(cells=cell_str)


# TRL vs Threat divergence threshold: if |trl_score_high - threat_numeric| >= this value, flag divergence.
TRL_THREAT_DIVERGENCE_THRESHOLD = 3

# Numeric mapping for threat levels (for divergence calculation).
THREAT_LEVEL_NUMERIC: dict[str, int] = {
    "low": 2,
    "medium": 5,
    "high": 8,
}
