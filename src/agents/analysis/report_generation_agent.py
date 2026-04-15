"""Report generation agent: synthesizes analysis results into a strategy report."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

from ...config.report_sections import (
    REQUIRED_SECTIONS,
    SECTION_IDS,
    THREAT_COMPOSITE_NOTICE,
    TRL_LIMITATION_NOTICE,
)
from ...config.report_warnings import (
    CONFLICT_FLAG,
    LOW_CONFIDENCE,
    MISSING_EVIDENCE,
    THREAT_LEVEL_NUMERIC,
    TRL_THREAT_DIVERGENCE,
    TRL_THREAT_DIVERGENCE_THRESHOLD,
    UNRESOLVED_CELL,
    format_warning,
)
from ...schemas.analysis_output_schema import (
    MergedAnalysisResult,
    PriorityBucket,
    PriorityMatrixRow,
)
from ...schemas.normalized_evidence_schema import NormalizedEvidence
from ...schemas.report_output_schema import (
    EvidenceTrace,
    ReportFormat,
    ReportOutput,
    ReportSection,
    ReportStatus,
    ReportWarning,
)


def _cell_label(item: MergedAnalysisResult | PriorityMatrixRow) -> str:
    return f"{item.technology}/{item.company}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _report_id(run_id: str) -> str:
    digest = hashlib.sha1(f"{run_id}{_now_iso()}".encode()).hexdigest()[:12]
    return f"report-{run_id[:8]}-{digest}"


def _trl_score_high(merged: MergedAnalysisResult) -> int | None:
    """Extract upper TRL score from trl_range string like '4-6' or '7'."""
    match = re.search(r"(\d+)(?:-(\d+))?", merged.trl_range)
    if match is None:
        return None
    high = match.group(2) or match.group(1)
    return int(high) if high else None


def _detect_trl_threat_divergence(merged: MergedAnalysisResult) -> bool:
    trl_high = _trl_score_high(merged)
    if trl_high is None:
        return False
    threat_numeric = THREAT_LEVEL_NUMERIC.get(merged.threat_level.value, 5)
    return abs(trl_high - threat_numeric) >= TRL_THREAT_DIVERGENCE_THRESHOLD


class ReportGenerationAgent:
    """Synthesizes MergedAnalysisResult + PriorityMatrixRow into a ReportOutput.

    This agent is rule-based for structure and section ordering.
    Sentence-level prose is assembled deterministically from structured fields;
    no LLM dependency is required but an optional llm_provider may be supplied
    for future narrative polishing.
    """

    def __init__(
        self,
        output_dir: str | Path = "data/analysis/reports",
        llm_provider: Any | None = None,
    ) -> None:
        self.output_dir = Path(output_dir)
        self.llm_provider = llm_provider

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(
        self,
        *,
        run_id: str,
        merged_results: Sequence[MergedAnalysisResult],
        priority_matrix: Sequence[PriorityMatrixRow],
        evidence_items: Iterable[NormalizedEvidence] | None = None,
        output_format: ReportFormat = ReportFormat.MARKDOWN,
    ) -> ReportOutput:
        evidence_map: dict[str, NormalizedEvidence] = {}
        if evidence_items is not None:
            for item in evidence_items:
                evidence_map[item.evidence_id] = item

        report_id = _report_id(run_id)

        warnings = self._collect_warnings(merged_results)
        sections = self._build_sections(merged_results, priority_matrix, evidence_map)
        reference_trace = self._build_reference_trace(merged_results, evidence_map)

        status = self._determine_status(merged_results, warnings)

        markdown_text = self._render_markdown(sections, reference_trace, warnings)

        self.output_dir.mkdir(parents=True, exist_ok=True)
        md_path = self.output_dir / f"{report_id}.md"
        md_path.write_text(markdown_text, encoding="utf-8")

        html_path = ""
        if output_format == ReportFormat.HTML:
            html_text = self._render_html(markdown_text)
            html_file = self.output_dir / f"{report_id}.html"
            html_file.write_text(html_text, encoding="utf-8")
            html_path = str(html_file)

        # PDF: placeholder — actual PDF conversion not implemented.
        pdf_path = str(self.output_dir / f"{report_id}.pdf.placeholder")

        report = ReportOutput(
            report_id=report_id,
            run_id=run_id,
            format=output_format,
            status=status,
            sections=sections,
            reference_trace=reference_trace,
            warnings=warnings,
            output_path=str(md_path),
            html_path=html_path,
            pdf_path=pdf_path,
            created_at=_now_iso(),
            metadata={
                "merged_count": len(merged_results),
                "evidence_count": len(evidence_map),
            },
        )
        return report

    # ------------------------------------------------------------------
    # Warning collection
    # ------------------------------------------------------------------

    def _collect_warnings(
        self, merged_results: Sequence[MergedAnalysisResult]
    ) -> list[ReportWarning]:
        warnings: list[ReportWarning] = []

        unresolved_cells = [_cell_label(m) for m in merged_results if m.unresolved]
        if unresolved_cells:
            warnings.append(
                ReportWarning(
                    code=UNRESOLVED_CELL.code,
                    message=format_warning(UNRESOLVED_CELL, unresolved_cells),
                    affected_cells=unresolved_cells,
                )
            )

        conflict_cells = [_cell_label(m) for m in merged_results if m.conflict_flag]
        if conflict_cells:
            warnings.append(
                ReportWarning(
                    code=CONFLICT_FLAG.code,
                    message=format_warning(CONFLICT_FLAG, conflict_cells),
                    affected_cells=conflict_cells,
                )
            )

        low_conf_cells = [
            _cell_label(m)
            for m in merged_results
            if m.merged_confidence.value == "low" and not m.unresolved
        ]
        if low_conf_cells:
            warnings.append(
                ReportWarning(
                    code=LOW_CONFIDENCE.code,
                    message=format_warning(LOW_CONFIDENCE, low_conf_cells),
                    affected_cells=low_conf_cells,
                )
            )

        divergence_cells = [
            _cell_label(m) for m in merged_results if _detect_trl_threat_divergence(m)
        ]
        if divergence_cells:
            warnings.append(
                ReportWarning(
                    code=TRL_THREAT_DIVERGENCE.code,
                    message=format_warning(TRL_THREAT_DIVERGENCE, divergence_cells),
                    affected_cells=divergence_cells,
                )
            )

        return warnings

    # ------------------------------------------------------------------
    # Section builders
    # ------------------------------------------------------------------

    def _build_sections(
        self,
        merged_results: Sequence[MergedAnalysisResult],
        priority_matrix: Sequence[PriorityMatrixRow],
        evidence_map: dict[str, NormalizedEvidence],
    ) -> list[ReportSection]:
        return [
            self._section_summary(merged_results),
            self._section_background(merged_results),
            self._section_technology_status(merged_results, evidence_map),
            self._section_competitor_trends(merged_results, evidence_map),
            self._section_strategic_implications(priority_matrix),
            self._section_reference(merged_results, evidence_map),
        ]

    def _section_summary(
        self, merged_results: Sequence[MergedAnalysisResult]
    ) -> ReportSection:
        immediate = [m for m in merged_results if m.priority_bucket == PriorityBucket.IMMEDIATE_PRIORITY]
        strategic = [m for m in merged_results if m.priority_bucket == PriorityBucket.STRATEGIC_WATCH]
        emerging = [m for m in merged_results if m.priority_bucket == PriorityBucket.EMERGING_RISK]
        unresolved = [m for m in merged_results if m.unresolved]
        conflict = [m for m in merged_results if m.conflict_flag]

        lines: list[str] = []

        if immediate:
            items = ", ".join(f"{m.technology}/{m.company}" for m in immediate)
            lines.append(f"**즉각 대응 필요 항목**: {items}.")
        if strategic:
            items = ", ".join(f"{m.technology}/{m.company}" for m in strategic)
            lines.append(f"**전략적 감시 필요 항목**: {items}.")
        if emerging:
            items = ", ".join(f"{m.technology}/{m.company}" for m in emerging)
            lines.append(f"**신흥 리스크 항목**: {items}.")
        if not immediate and not strategic and not emerging:
            lines.append("현재 즉각 대응이 필요한 고위협 항목은 식별되지 않았습니다.")

        if unresolved:
            items = ", ".join(_cell_label(m) for m in unresolved)
            lines.append(f"**미완료 분석 셀** ({items})이 존재하며 추가 검토가 필요합니다.")
        if conflict:
            items = ", ".join(_cell_label(m) for m in conflict)
            lines.append(f"**상충 항목** ({items})이 감지되었습니다. 해석 시 주의가 필요합니다.")

        body = "\n\n".join(lines)
        return ReportSection(section_id="summary", title="SUMMARY", body=body)

    def _section_background(
        self, merged_results: Sequence[MergedAnalysisResult]
    ) -> ReportSection:
        technologies = sorted({m.technology for m in merged_results})
        companies = sorted({m.company for m in merged_results})

        lines = [
            f"분석 대상 기술 축: {', '.join(technologies)}",
            f"분석 대상 기업: {', '.join(companies)}",
            "",
            "**분석 방법론**: quality-passed normalized evidence를 기반으로 "
            "TRL 수준과 위협 수준을 분리 분석한 뒤 병합(merge) 및 우선순위 매트릭스를 생성하였습니다.",
            "",
            TRL_LIMITATION_NOTICE,
            "",
            THREAT_COMPOSITE_NOTICE,
        ]
        body = "\n".join(lines)
        return ReportSection(section_id="background", title="분석 배경", body=body)

    def _section_technology_status(
        self,
        merged_results: Sequence[MergedAnalysisResult],
        evidence_map: dict[str, NormalizedEvidence],
    ) -> ReportSection:
        subsections: list[ReportSection] = []
        claim_ids: list[str] = []

        for tech in sorted({m.technology for m in merged_results}):
            tech_items = sorted(
                [m for m in merged_results if m.technology == tech],
                key=lambda m: m.company,
            )
            lines: list[str] = []
            tech_claim_ids: list[str] = []

            for m in tech_items:
                claim_id = f"trl-{m.technology}-{m.company}".replace(" ", "_").lower()
                tech_claim_ids.append(claim_id)
                claim_ids.append(claim_id)

                trl_line = f"- **{m.company}**: TRL {m.trl_range} (신뢰도: {m.merged_confidence.value})"
                if m.unresolved:
                    trl_line += " ⚠ 미완료"
                if m.conflict_flag:
                    trl_line += " ⚠ 상충"
                lines.append(trl_line)

                # Reference trace: prefer direct evidence reference
                ref_id = m.trl_reference_id
                if ref_id and ref_id in evidence_map:
                    ev = evidence_map[ref_id]
                    raw_excerpt = (ev.raw_content[:200] + "...") if len(ev.raw_content) > 200 else ev.raw_content
                    lines.append(f"  근거: {raw_excerpt} `[REF:{ref_id}]`")
                elif ref_id:
                    lines.append(f"  근거: `[REF:{ref_id}]`")

                # TRL-Threat divergence explanation
                if _detect_trl_threat_divergence(m):
                    threat_val = THREAT_LEVEL_NUMERIC.get(m.threat_level.value, 5)
                    trl_high = _trl_score_high(m)
                    lines.append(
                        f"  ※ **TRL-위협 수준 괴리**: TRL {m.trl_range} 대비 위협 수준이 "
                        f"{m.threat_level.value}({threat_val}/10)으로 평가되었습니다. "
                        "이는 실행 신뢰도(Execution Credibility)나 전략 중첩도(Strategic Overlap)가 "
                        "기술 성숙도보다 높은 경우에 발생할 수 있으며, "
                        "시장 선점 전략 또는 파트너십 동향을 추가로 검토할 필요가 있습니다."
                    )

                if m.notes:
                    for note in m.notes:
                        lines.append(f"  [메모] {note}")

            if lines:
                subsections.append(
                    ReportSection(
                        section_id=f"technology_status_{tech}".replace(" ", "_").lower(),
                        title=tech,
                        body="\n".join(lines),
                        claim_ids=tech_claim_ids,
                    )
                )

        header_lines = [
            TRL_LIMITATION_NOTICE,
            "",
            "각 기술 축별 TRL 수준 분석 결과는 아래와 같습니다.",
        ]
        return ReportSection(
            section_id="technology_status",
            title="기술 현황",
            body="\n".join(header_lines),
            claim_ids=claim_ids,
            subsections=subsections,
        )

    def _section_competitor_trends(
        self,
        merged_results: Sequence[MergedAnalysisResult],
        evidence_map: dict[str, NormalizedEvidence],
    ) -> ReportSection:
        subsections: list[ReportSection] = []
        claim_ids: list[str] = []

        for company in sorted({m.company for m in merged_results}):
            company_items = sorted(
                [m for m in merged_results if m.company == company],
                key=lambda m: m.technology,
            )
            lines: list[str] = []
            company_claim_ids: list[str] = []

            for m in company_items:
                claim_id = f"threat-{m.technology}-{m.company}".replace(" ", "_").lower()
                company_claim_ids.append(claim_id)
                claim_ids.append(claim_id)

                threat_line = (
                    f"- **{m.technology}**: 위협 수준={m.threat_level.value.upper()}, "
                    f"우선순위={m.priority_bucket.value}, 신뢰도={m.merged_confidence.value}"
                )
                if m.unresolved:
                    threat_line += " ⚠ 재검토 필요"
                if m.conflict_flag:
                    threat_line += " ⚠ 상충"
                lines.append(threat_line)

                ref_id = m.threat_reference_id
                if ref_id and ref_id in evidence_map:
                    ev = evidence_map[ref_id]
                    raw_excerpt = (ev.raw_content[:200] + "...") if len(ev.raw_content) > 200 else ev.raw_content
                    lines.append(f"  근거: {raw_excerpt} `[REF:{ref_id}]`")
                elif ref_id:
                    lines.append(f"  근거: `[REF:{ref_id}]`")

                if _detect_trl_threat_divergence(m):
                    lines.append(
                        f"  ※ TRL {m.trl_range}에 비해 위협 수준이 {m.threat_level.value}으로 평가된 배경: "
                        "높은 Execution Credibility 또는 Strategic Overlap 점수가 위협 수준을 끌어올린 것으로 분석됩니다. "
                        f"action_hint: {m.action_hint}"
                    )

                lines.append(f"  권고: {m.action_hint}")

            if lines:
                subsections.append(
                    ReportSection(
                        section_id=f"competitor_{company}".replace(" ", "_").lower(),
                        title=company,
                        body="\n".join(lines),
                        claim_ids=company_claim_ids,
                    )
                )

        header_lines = [
            THREAT_COMPOSITE_NOTICE,
            "",
            "기업별 위협 수준 및 동향 분석 결과는 아래와 같습니다.",
        ]
        return ReportSection(
            section_id="competitor_trends",
            title="경쟁사 동향",
            body="\n".join(header_lines),
            claim_ids=claim_ids,
            subsections=subsections,
        )

    def _section_strategic_implications(
        self, priority_matrix: Sequence[PriorityMatrixRow]
    ) -> ReportSection:
        buckets: dict[str, list[PriorityMatrixRow]] = {
            PriorityBucket.IMMEDIATE_PRIORITY.value: [],
            PriorityBucket.STRATEGIC_WATCH.value: [],
            PriorityBucket.EMERGING_RISK.value: [],
            PriorityBucket.MONITOR.value: [],
            PriorityBucket.REVIEW_REQUIRED.value: [],
        }
        for row in priority_matrix:
            buckets.setdefault(row.priority_bucket.value, []).append(row)

        lines: list[str] = []

        bucket_labels: list[tuple[str, str, str]] = [
            (PriorityBucket.IMMEDIATE_PRIORITY.value, "즉각 대응 (Immediate Priority)", "즉각적인 전략적 대응이 필요합니다."),
            (PriorityBucket.STRATEGIC_WATCH.value, "전략적 감시 (Strategic Watch)", "지속적인 모니터링과 대응 계획 수립이 필요합니다."),
            (PriorityBucket.EMERGING_RISK.value, "신흥 리스크 (Emerging Risk)", "조기 경보 체계 구축을 권장합니다."),
            (PriorityBucket.REVIEW_REQUIRED.value, "재검토 필요 (Review Required)", "분석 데이터 보완 후 재평가가 필요합니다."),
            (PriorityBucket.MONITOR.value, "모니터링 (Monitor)", "현재 수준에서 지속 관찰을 유지합니다."),
        ]

        for bucket_val, label, action in bucket_labels:
            rows = buckets.get(bucket_val, [])
            if not rows:
                continue
            lines.append(f"### {label}")
            lines.append(f"{action}")
            lines.append("")
            for row in sorted(rows, key=lambda r: (r.technology, r.company)):
                lines.append(
                    f"- **{row.technology}/{row.company}**: "
                    f"TRL {row.trl_range}, 위협={row.threat_level.value}, "
                    f"신뢰도={row.merged_confidence.value}"
                )
                lines.append(f"  → {row.action_hint}")
            lines.append("")

        body = "\n".join(lines) if lines else "우선순위 매트릭스 데이터가 없습니다."
        return ReportSection(
            section_id="strategic_implications",
            title="전략적 시사점",
            body=body,
        )

    def _section_reference(
        self,
        merged_results: Sequence[MergedAnalysisResult],
        evidence_map: dict[str, NormalizedEvidence],
    ) -> ReportSection:
        seen: set[str] = set()
        ref_lines: list[str] = []
        missing: list[str] = []

        all_ref_ids: list[str] = []
        for m in merged_results:
            if m.trl_reference_id:
                all_ref_ids.append(m.trl_reference_id)
            if m.threat_reference_id:
                all_ref_ids.append(m.threat_reference_id)

        for ref_id in sorted(set(all_ref_ids)):
            if ref_id in seen:
                continue
            seen.add(ref_id)
            if ref_id in evidence_map:
                ev = evidence_map[ref_id]
                ref_lines.append(
                    f"- `[{ref_id}]` {ev.title} | {ev.source_name} | {ev.published_at} | {ev.url}"
                )
            else:
                missing.append(ref_id)
                ref_lines.append(f"- `[{ref_id}]` *(evidence 정보 없음)*")

        if missing:
            ref_lines.append("")
            ref_lines.append(f"※ evidence 정보 누락: {', '.join(missing)}")

        body = "\n".join(ref_lines) if ref_lines else "참조 evidence 없음."
        return ReportSection(section_id="reference", title="REFERENCE", body=body)

    # ------------------------------------------------------------------
    # Reference trace builder
    # ------------------------------------------------------------------

    def _build_reference_trace(
        self,
        merged_results: Sequence[MergedAnalysisResult],
        evidence_map: dict[str, NormalizedEvidence],
    ) -> list[EvidenceTrace]:
        traces: list[EvidenceTrace] = []
        seen: set[tuple[str, str]] = set()

        for m in merged_results:
            for ref_id, claim_prefix in [
                (m.trl_reference_id, "trl"),
                (m.threat_reference_id, "threat"),
            ]:
                if not ref_id:
                    continue
                claim_id = f"{claim_prefix}-{m.technology}-{m.company}".replace(" ", "_").lower()
                key = (claim_id, ref_id)
                if key in seen:
                    continue
                seen.add(key)

                if ref_id in evidence_map:
                    ev = evidence_map[ref_id]
                    quote = ev.raw_content[:300] if ev.raw_content else ""
                    traces.append(
                        EvidenceTrace(
                            claim_id=claim_id,
                            evidence_id=ref_id,
                            source_name=ev.source_name,
                            url=ev.url,
                            published_at=ev.published_at,
                            quote=quote,
                        )
                    )
                else:
                    traces.append(
                        EvidenceTrace(
                            claim_id=claim_id,
                            evidence_id=ref_id,
                            source_name="",
                            url="",
                            published_at="",
                            quote="",
                        )
                    )

        return sorted(traces, key=lambda t: (t.claim_id, t.evidence_id))

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _render_markdown(
        self,
        sections: list[ReportSection],
        reference_trace: list[EvidenceTrace],
        warnings: list[ReportWarning],
    ) -> str:
        parts: list[str] = []

        for section in sections:
            parts.append(f"# {section.title}")
            if section.body:
                parts.append(section.body)
            for sub in section.subsections:
                parts.append(f"## {sub.title}")
                if sub.body:
                    parts.append(sub.body)
                for subsub in sub.subsections:
                    parts.append(f"### {subsub.title}")
                    if subsub.body:
                        parts.append(subsub.body)
            parts.append("")

        if warnings:
            parts.append("---")
            parts.append("# ⚠ 경고 및 제한사항")
            for w in warnings:
                parts.append(f"- **[{w.code}]** {w.message}")
            parts.append("")

        return "\n\n".join(parts)

    def _render_html(self, markdown_text: str) -> str:
        """Minimal HTML wrapper around raw markdown text (no external dependency)."""
        escaped = markdown_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return (
            "<!DOCTYPE html><html><head>"
            '<meta charset="utf-8"><title>Technology Strategy Report</title>'
            "<style>body{font-family:sans-serif;max-width:900px;margin:auto;padding:2em}"
            "pre{background:#f4f4f4;padding:1em}h1,h2,h3{color:#222}</style>"
            "</head><body><pre>"
            + escaped
            + "</pre></body></html>"
        )

    # ------------------------------------------------------------------
    # Status determination
    # ------------------------------------------------------------------

    def _determine_status(
        self,
        merged_results: Sequence[MergedAnalysisResult],
        warnings: list[ReportWarning],
    ) -> ReportStatus:
        if all(m.unresolved for m in merged_results):
            return ReportStatus.BLOCKED
        if any(w.code in ("UNRESOLVED_CELL", "CONFLICT_FLAG") for w in warnings):
            return ReportStatus.WARNING
        if warnings:
            return ReportStatus.WARNING
        return ReportStatus.READY
