from __future__ import annotations

import unittest

from src.normalization.evidence_normalizer import EvidenceNormalizer
from src.schemas.raw_result_schema import RawFinding


class EvidenceNormalizerTest(unittest.TestCase):
    def test_normalize_finding_preserves_canonical_fields(self) -> None:
        finding = RawFinding(
            raw_finding_id="run-1:pim:1",
            run_id="run-1",
            agent_type="pim",
            query="PIM architecture",
            title="PIM architecture update",
            source_type="news",
            signal_type="direct",
            source_name="Example Source",
            published_at="2025-01-15T00:00:00Z",
            url="https://example.invalid/pim/1",
            raw_content="PIM architecture update. Customer collaboration signal.",
            key_points=[],
            company=["SK hynix"],
            technology="PIM",
            signals=["pim_signal"],
            counter_signals=[],
            confidence="high",
            metadata={"region": "global"},
        )

        normalized = EvidenceNormalizer().normalize_finding(finding)

        self.assertEqual(normalized.evidence_id, finding.raw_finding_id)
        self.assertEqual(normalized.run_id, "run-1")
        self.assertEqual(normalized.signal_type, "direct")
        self.assertEqual(normalized.company, ["SK hynix"])
        self.assertTrue(normalized.quality_passed)
        self.assertFalse(normalized.unresolved)
        self.assertGreaterEqual(len(normalized.key_points), 1)

    def test_normalize_finding_marks_failed_local_validation_unresolved(self) -> None:
        finding = RawFinding(
            raw_finding_id="run-1:pim:2",
            run_id="run-1",
            agent_type="pim",
            query="PIM architecture",
            title="PIM architecture update",
            source_type="news",
            signal_type="direct",
            source_name="Example Source",
            published_at="2025-01-15T00:00:00Z",
            url="https://example.invalid/pim/2",
            raw_content="PIM architecture update.",
            company=["SK hynix"],
            technology="PIM",
            confidence="medium",
            local_validation={"passed": False},
        )

        normalized = EvidenceNormalizer().normalize_finding(finding)

        self.assertFalse(normalized.quality_passed)
        self.assertTrue(normalized.unresolved)


if __name__ == "__main__":
    unittest.main()
