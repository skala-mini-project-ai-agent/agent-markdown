"""Canonical section definitions for the technology strategy report."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SectionSpec:
    section_id: str
    title: str
    required: bool = True
    description: str = ""


# Ordered list of sections that MUST appear in every report.
REQUIRED_SECTIONS: list[SectionSpec] = [
    SectionSpec(
        section_id="summary",
        title="SUMMARY",
        required=True,
        description="Executive summary of the analysis findings.",
    ),
    SectionSpec(
        section_id="background",
        title="분석 배경",
        required=True,
        description="Context, scope, and methodology of the analysis.",
    ),
    SectionSpec(
        section_id="technology_status",
        title="기술 현황",
        required=True,
        description="TRL-based technology maturity assessment per technology axis.",
    ),
    SectionSpec(
        section_id="competitor_trends",
        title="경쟁사 동향",
        required=True,
        description="Threat-level assessment and observed competitor activities.",
    ),
    SectionSpec(
        section_id="strategic_implications",
        title="전략적 시사점",
        required=True,
        description="Priority matrix interpretation and recommended actions.",
    ),
    SectionSpec(
        section_id="reference",
        title="REFERENCE",
        required=True,
        description="Full reference list with evidence traces.",
    ),
]

SECTION_IDS: list[str] = [s.section_id for s in REQUIRED_SECTIONS]

# TRL 4-6 estimation limitation notice inserted into technology_status section.
TRL_LIMITATION_NOTICE = (
    "※ TRL 4~6 구간 추정은 간접 증거(특허, 채용 공고, 컨퍼런스 발표 등)에 의존하며 "
    "실제 개발 성숙도와 차이가 있을 수 있습니다. 해당 구간의 수치는 추정 범위로 해석해야 합니다."
)

# Threat level composite factor notice inserted into competitor_trends section.
THREAT_COMPOSITE_NOTICE = (
    "※ 위협 수준 평가는 TRL 외에도 Impact(사업 영향), Immediacy(실행 시점), "
    "Execution Credibility(실행 신뢰도), Strategic Overlap(전략 중첩도) 등 복합 요인을 반영합니다."
)
