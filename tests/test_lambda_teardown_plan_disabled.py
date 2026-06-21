import pytest

from decodilo.errors import LaunchDisabledError
from decodilo.lambda_cloud.teardown_plan import (
    LambdaTeardownPlan,
    build_lambda_teardown_plan,
    execute_lambda_teardown_plan,
)


def test_lambda_teardown_plan_disabled_and_empty_live_ids() -> None:
    plan = build_lambda_teardown_plan(run_id="run-1", planned_node_ids=["node-0"])

    assert plan.teardown_enabled is False
    assert plan.live_resource_ids == []
    with pytest.raises(LaunchDisabledError):
        execute_lambda_teardown_plan(plan)


def test_lambda_teardown_plan_rejects_live_resource_ids() -> None:
    with pytest.raises(ValueError):
        LambdaTeardownPlan(run_id="bad", live_resource_ids=["i-live"])
