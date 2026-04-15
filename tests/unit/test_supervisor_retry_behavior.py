from types import SimpleNamespace

from src.schemas.quality_report_schema import QualityReport
from src.schemas.supervisor_state_schema import RetryPlan, RetryTarget
from src.supervisor.supervisor import CentralSupervisor


class _SequenceSearchRunner:
    def __init__(self, results):
        self.results = list(results)
        self.calls = 0

    def run(self, context):
        index = min(self.calls, len(self.results) - 1)
        self.calls += 1
        return self.results[index]


class _RetryControllerStub:
    def __init__(self, plans):
        self.plans = list(plans)
        self.calls = 0

    def build_retry_plan(self, **kwargs):
        index = min(self.calls, len(self.plans) - 1)
        self.calls += 1
        plan = self.plans[index]
        if callable(plan):
            return plan(**kwargs)
        return plan


def _quality(
    *,
    status: str = "fail",
    low_evidence: int = 1,
    low_confidence: int = 0,
    conflicts: int = 0,
    bias: int = 0,
):
    return QualityReport(
        run_id="run-test",
        status=status,
        low_evidence_cells=[{"technology": "HBM4", "company": "Micron"}] * low_evidence,
        low_confidence_cells=[{"technology": "HBM4", "company": "Micron"}] * low_confidence,
        conflict_flags=[{"technology": "HBM4", "company": "Micron", "reason": "conflict"}] * conflicts,
        bias_flags=[{"type": "company_bias", "company": "Micron"}] * bias,
        analysis_ready=(status == "pass"),
    )


def _result(quality_report):
    return SimpleNamespace(quality_report=quality_report, normalized_evidence=[])


def test_search_retry_stops_early_when_fail_signature_repeats():
    supervisor = CentralSupervisor()
    supervisor.search_runner = _SequenceSearchRunner([
        _result(_quality(status="fail", low_evidence=2)),
        _result(_quality(status="fail", low_evidence=2)),
        _result(_quality(status="pass", low_evidence=0)),
    ])
    supervisor.retry_controller = _RetryControllerStub(
        [
            lambda **kwargs: RetryPlan(
                run_id="run-test",
                retry_targets=[RetryTarget(agent="hbm4", technology="HBM4", company="Micron", reason="low_evidence")],
                retry_allowed=True,
                retry_count=kwargs["current_retry_count"] + 1,
                unresolved_allowed=False,
            ),
            lambda **kwargs: RetryPlan(
                run_id="run-test",
                retry_targets=[RetryTarget(agent="hbm4", technology="HBM4", company="Micron", reason="low_evidence")],
                retry_allowed=True,
                retry_count=kwargs["current_retry_count"] + 1,
                unresolved_allowed=False,
            ),
        ]
    )
    state, context = supervisor.planner.create_state(
        run_id="run-test",
        user_query="HBM4 scan",
        technology_axes=["HBM4"],
        seed_competitors=["Micron"],
    )

    result = supervisor._run_search_with_retry(state, context.to_search_context())

    assert result.quality_report.status == "fail"
    assert supervisor.search_runner.calls == 2


def test_search_retry_continues_when_quality_improves():
    supervisor = CentralSupervisor()
    supervisor.search_runner = _SequenceSearchRunner([
        _result(_quality(status="fail", low_evidence=3, low_confidence=1)),
        _result(_quality(status="warning", low_evidence=0, low_confidence=1)),
        _result(_quality(status="pass", low_evidence=0, low_confidence=0)),
    ])
    supervisor.retry_controller = _RetryControllerStub(
        [
            lambda **kwargs: RetryPlan(
                run_id="run-test",
                retry_targets=[RetryTarget(agent="hbm4", technology="HBM4", company="Micron", reason="low_evidence")],
                retry_allowed=True,
                retry_count=kwargs["current_retry_count"] + 1,
                unresolved_allowed=False,
            ),
            lambda **kwargs: RetryPlan(
                run_id="run-test",
                retry_targets=[RetryTarget(agent="hbm4", technology="HBM4", company="Micron", reason="low_evidence")],
                retry_allowed=True,
                retry_count=kwargs["current_retry_count"] + 1,
                unresolved_allowed=False,
            ),
        ]
    )
    state, context = supervisor.planner.create_state(
        run_id="run-test",
        user_query="HBM4 scan",
        technology_axes=["HBM4"],
        seed_competitors=["Micron"],
    )

    result = supervisor._run_search_with_retry(state, context.to_search_context())

    assert result.quality_report.status == "pass"
    assert supervisor.search_runner.calls == 3
