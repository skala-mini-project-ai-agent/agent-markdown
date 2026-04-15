from __future__ import annotations

import unittest

from src.agents.base.base_agent import SearchExecutionContext
from src.orchestration.parallel_search_runner import ParallelSearchRunner


class ParallelSearchRunnerTest(unittest.TestCase):
    def test_runner_executes_all_search_agents(self) -> None:
        runner = ParallelSearchRunner()
        context = SearchExecutionContext(
            run_id="run-smoke",
            user_query="global memory technology trends",
            technology_axes=["HBM4", "PIM", "CXL", "Advanced Packaging", "Thermal Power"],
            seed_competitors=["SK hynix", "Micron"],
            freshness_start_year=2024,
            open_exploration_mode=True,
        )

        result = runner.run(context)

        self.assertEqual(result.run_id, "run-smoke")
        self.assertEqual(len(result.agents), 6)
        self.assertGreater(len(result.normalized_evidence), 0)
        self.assertIsNotNone(result.quality_report)
        self.assertEqual(result.quality_report.run_id, "run-smoke")
        self.assertIn(result.quality_report.status, {"pass", "warning"})


if __name__ == "__main__":
    unittest.main()

