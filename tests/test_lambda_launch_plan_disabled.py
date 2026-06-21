import pytest

from decodilo.errors import LaunchDisabledError
from decodilo.lambda_cloud.launch_plan import build_lambda_launch_plan, execute_lambda_launch_plan


def test_lambda_launch_plan_serializes_and_cannot_execute() -> None:
    plan = build_lambda_launch_plan(
        run_id="run-1",
        instance_type="gpu_8x_h100_sxm",
        region="us-west-1",
        nodes=1,
        gpus_per_instance=8,
        hours=1,
        max_run_budget=100,
    )

    assert plan.launch_enabled is False
    assert plan.launch_allowed is False
    assert plan.to_json()
    with pytest.raises(LaunchDisabledError):
        execute_lambda_launch_plan(plan)


def test_lambda_launch_plan_cannot_be_enabled() -> None:
    with pytest.raises(ValueError):
        from decodilo.lambda_cloud.launch_plan import LambdaLaunchPlan

        LambdaLaunchPlan(
            run_id="bad",
            instance_type="gpu_8x_h100_sxm",
            region="us-west-1",
            node_count=1,
            gpus_per_instance=8,
            planned_hours=1,
            max_runtime_minutes=60,
            max_run_budget=100,
            launch_allowed=True,
        )
