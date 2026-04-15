"""Convert raw findings into canonical normalized evidence."""

from __future__ import annotations

from dataclasses import dataclass

from src.normalization.keypoint_extractor import extract_key_points
from src.normalization.tagging import build_metadata, infer_company, infer_source_type, infer_technology
from src.schemas.normalized_evidence_schema import NormalizedEvidence
from src.schemas.raw_result_schema import RawFinding, RawSearchBundle


@dataclass(slots=True)
class EvidenceNormalizer:
    def normalize_finding(self, raw_finding: RawFinding) -> NormalizedEvidence:
        missing_field_flags: list[str] = []
        if not raw_finding.title:
            missing_field_flags.append("title")
        if not raw_finding.url:
            missing_field_flags.append("url")
        if not raw_finding.published_at:
            missing_field_flags.append("published_at")
        if not raw_finding.raw_content:
            missing_field_flags.append("raw_content")

        key_points = extract_key_points(raw_finding)
        conflict_candidate = bool(raw_finding.counter_signals)
        unresolved = bool(missing_field_flags) or raw_finding.local_validation.get("passed") is False
        return NormalizedEvidence(
            evidence_id=raw_finding.raw_finding_id,
            run_id=raw_finding.run_id,
            agent_type=raw_finding.agent_type,
            technology=infer_technology(raw_finding),
            company=infer_company(raw_finding),
            title=raw_finding.title,
            source_type=infer_source_type(raw_finding),
            signal_type=raw_finding.signal_type,
            source_name=raw_finding.source_name,
            published_at=raw_finding.published_at,
            url=raw_finding.url,
            raw_content=raw_finding.raw_content,
            key_points=key_points,
            signals=list(raw_finding.signals),
            counter_signals=list(raw_finding.counter_signals),
            confidence=raw_finding.confidence,
            quality_passed=not unresolved,
            conflict_candidate=conflict_candidate,
            unresolved=unresolved,
            metadata=build_metadata(raw_finding),
            missing_field_flags=missing_field_flags,
        )

    def normalize_bundle(self, raw_bundle: RawSearchBundle) -> list[NormalizedEvidence]:
        return [self.normalize_finding(finding) for finding in raw_bundle.raw_findings]

