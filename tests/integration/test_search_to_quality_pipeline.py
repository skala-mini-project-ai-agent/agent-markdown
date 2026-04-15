from __future__ import annotations

import unittest

from src.agents.base.base_agent import SearchExecutionContext
from src.orchestration.parallel_search_runner import ParallelSearchRunner


class SearchToQualityPipelineTest(unittest.TestCase):
    def test_end_to_end_smoke(self) -> None:
        runner = ParallelSearchRunner()
        result = runner.run(
            SearchExecutionContext(
                run_id="run-e2e",
                user_query="HBM4 and CXL strategic scan",
                technology_axes=["HBM4", "CXL"],
                seed_competitors=["SK hynix", "Micron"],
                freshness_start_year=2024,
                open_exploration_mode=True,
            )
        )

        self.assertGreaterEqual(len(result.normalized_evidence), 1)
        self.assertIsNotNone(result.quality_report)
        self.assertEqual(result.quality_report.run_id, "run-e2e")


if __name__ == "__main__":
    unittest.main()

