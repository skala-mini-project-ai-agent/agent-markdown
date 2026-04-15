from __future__ import annotations

import unittest

from src.normalization.evidence_normalizer import EvidenceNormalizer
from src.quality.quality_gate import QualityGate
from src.schemas.raw_result_schema import RawFinding


class QualityGateTest(unittest.TestCase):
    def test_quality_gate_passes_for_balanced_evidence(self) -> None:
        raw_findings = [
            RawFinding(
                raw_finding_id="run-2:hbm4:1",
                run_id="run-2",
                agent_type="hbm4",
                query="HBM4 roadmap",
                title="HBM4 roadmap update",
                source_type="news",
                signal_type="direct",
                source_name="Source A",
                published_at="2025-01-01T00:00:00Z",
                url="https://example.invalid/hbm4/a",
                raw_content="HBM4 roadmap update.",
                company=["SK hynix"],
                technology="HBM4",
                confidence="high",
            ),
            RawFinding(
                raw_finding_id="run-2:hbm4:2",
                run_id="run-2",
                agent_type="hbm4",
                query="HBM4 roadmap",
                title="HBM4 roadmap update",
                source_type="paper",
                signal_type="direct",
                source_name="Source B",
                published_at="2025-01-02T00:00:00Z",
                url="https://example.invalid/hbm4/b",
                raw_content="HBM4 performance validation.",
                company=["Micron"],
                technology="HBM4",
                confidence="high",
            ),
            RawFinding(
                raw_finding_id="run-2:cxl:1",
                run_id="run-2",
                agent_type="cxl",
                query="CXL adoption",
                title="CXL adoption update",
                source_type="news",
                signal_type="direct",
                source_name="Source C",
                published_at="2025-01-03T00:00:00Z",
                url="https://example.invalid/cxl/a",
                raw_content="CXL adoption update.",
                company=["SK hynix"],
                technology="CXL",
                confidence="high",
            ),
            RawFinding(
                raw_finding_id="run-2:cxl:2",
                run_id="run-2",
                agent_type="cxl",
                query="CXL adoption",
                title="CXL adoption update",
                source_type="paper",
                signal_type="direct",
                source_name="Source D",
                published_at="2025-01-04T00:00:00Z",
                url="https://example.invalid/cxl/b",
                raw_content="CXL adoption update.",
                company=["Micron"],
                technology="CXL",
                confidence="high",
            ),
            RawFinding(
                raw_finding_id="run-2:hbm4:3",
                run_id="run-2",
                agent_type="hbm4",
                query="HBM4 roadmap",
                title="HBM4 roadmap expansion",
                source_type="news",
                signal_type="direct",
                source_name="Source E",
                published_at="2025-01-05T00:00:00Z",
                url="https://example.invalid/hbm4/c",
                raw_content="HBM4 roadmap expansion.",
                company=["SK hynix"],
                technology="HBM4",
                confidence="high",
            ),
            RawFinding(
                raw_finding_id="run-2:hbm4:4",
                run_id="run-2",
                agent_type="hbm4",
                query="HBM4 roadmap",
                title="HBM4 roadmap expansion",
                source_type="paper",
                signal_type="direct",
                source_name="Source F",
                published_at="2025-01-06T00:00:00Z",
                url="https://example.invalid/hbm4/d",
                raw_content="HBM4 roadmap expansion.",
                company=["Micron"],
                technology="HBM4",
                confidence="high",
            ),
            RawFinding(
                raw_finding_id="run-2:cxl:3",
                run_id="run-2",
                agent_type="cxl",
                query="CXL adoption",
                title="CXL adoption expansion",
                source_type="news",
                signal_type="direct",
                source_name="Source G",
                published_at="2025-01-07T00:00:00Z",
                url="https://example.invalid/cxl/c",
                raw_content="CXL adoption expansion.",
                company=["SK hynix"],
                technology="CXL",
                confidence="high",
            ),
            RawFinding(
                raw_finding_id="run-2:cxl:4",
                run_id="run-2",
                agent_type="cxl",
                query="CXL adoption",
                title="CXL adoption expansion",
                source_type="paper",
                signal_type="direct",
                source_name="Source H",
                published_at="2025-01-08T00:00:00Z",
                url="https://example.invalid/cxl/d",
                raw_content="CXL adoption expansion.",
                company=["Micron"],
                technology="CXL",
                confidence="high",
            ),
        ]

        normalized = [EvidenceNormalizer().normalize_finding(item) for item in raw_findings]
        report = QualityGate().evaluate("run-2", normalized)

        self.assertEqual(report.status, "pass")
        self.assertTrue(report.analysis_ready)
        self.assertEqual(report.coverage["total_records"], 8)
        self.assertEqual(report.low_evidence_cells, [])


if __name__ == "__main__":
    unittest.main()
