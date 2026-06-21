import pytest

from decodilo.cloud.disabled_launcher import DisabledCloudLauncher
from decodilo.cloud.launch_plan import CloudLaunchPlan
from decodilo.cloud.launcher_interface import LaunchRequest
from decodilo.errors import LaunchDisabledError
from decodilo.lambda_cloud.launch_plan import build_lambda_launch_plan


def test_cloud_launcher_remains_disabled_m018() -> None:
    launcher = DisabledCloudLauncher()
    request = LaunchRequest(
        plan=CloudLaunchPlan(
            run_id="m018",
            provider="lambda",
            node_count=1,
            instance_type="sample",
            gpu_type="sample",
            gpus_per_instance=1,
            total_gpus=1,
            planned_hours=1,
            price_snapshot_id="sample",
            selected_price_record_id="sample",
            base_estimated_cost=0,
            safety_buffer_adjusted_cost=0,
            max_run_budget=0,
            starting_credits=0,
            projected_remaining_credits=0,
            launch_allowed=False,
        )
    )

    with pytest.raises(LaunchDisabledError):
        launcher.launch(request)


def test_lambda_plan_flags_remain_false_m018() -> None:
    plan = build_lambda_launch_plan(
        run_id="m018",
        instance_type="gpu_8x_h100_sxm",
        region="us-west-1",
        nodes=1,
        gpus_per_instance=8,
        hours=1,
        max_run_budget=100,
    )

    assert plan.launch_enabled is False
    assert plan.launch_allowed is False
