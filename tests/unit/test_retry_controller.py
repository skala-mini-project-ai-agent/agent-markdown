from src.config.settings import SupervisorSettings
from src.supervisor.retry_controller import RetryController


class DummyQualityReport:
    low_evidence_cells = [
        {"technology": "HBM4", "company": "Company A"},
        {"technology": "PIM", "company": "Company B"},
    ]


def test_retry_controller_creates_targeted_retry_plan():
    controller = RetryController(SupervisorSettings())
    plan = controller.build_retry_plan(run_id="r1", quality_report=DummyQualityReport(), current_retry_count=0)

    assert plan.retry_allowed is True
    assert plan.retry_count == 1
    assert len(plan.retry_targets) == 2
    assert plan.retry_targets[0].agent == "hbm4"


def test_retry_controller_stops_after_limit():
    controller = RetryController(SupervisorSettings())
    plan = controller.build_retry_plan(run_id="r1", quality_report=DummyQualityReport(), current_retry_count=2)

    assert plan.retry_allowed is False
    assert plan.unresolved_allowed is True
