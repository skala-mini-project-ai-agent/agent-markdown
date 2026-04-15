from src.config.settings import SupervisorSettings
from src.supervisor.planning import PlanningModule


def test_planning_defaults_to_open_exploration_mode():
    planner = PlanningModule(SupervisorSettings())
    state, context = planner.create_state(run_id="r1", user_query="HBM4 strategy")

    assert state.mode == "open_exploration_mode"
    assert context.open_exploration_mode is True
    assert "pim" in state.query_bundles
    assert state.stage_status["supervisor_planning"].value == "passed"


def test_planning_uses_seed_mode_when_competitors_given():
    planner = PlanningModule(SupervisorSettings())
    state, context = planner.create_state(
        run_id="r2",
        user_query="PIM strategic scan",
        seed_competitors=["SK hynix"],
    )

    assert state.mode == "seed_competitor_mode"
    assert context.open_exploration_mode is False
