import pytest

from decodilo.cloud.disabled_launcher import DisabledCloudLauncher
from decodilo.cloud.launch_plan import CloudLaunchPlan
from decodilo.cloud.launcher_interface import LaunchRequest
from decodilo.errors import LaunchDisabledError
from decodilo.lambda_cloud.real_launch_decision_record import (
    LambdaRealLaunchDecisionRecord,
)


def test_cloud_launcher_still_disabled_m026():
    plan = CloudLaunchPlan(
        run_id="m026",
        provider="lambda",
        node_count=1,
        instance_type="gpu_8x_h100_sxm",
        gpu_type="H100 SXM",
        gpus_per_instance=8,
        total_gpus=8,
        planned_hours=0.5,
        price_snapshot_id="snapshot",
        selected_price_record_id="record",
        base_estimated_cost=10,
        safety_buffer_adjusted_cost=11.5,
        max_run_budget=50,
        starting_credits=100,
        projected_remaining_credits=88.5,
        launch_allowed=False,
    )
    launcher = DisabledCloudLauncher()

    with pytest.raises(LaunchDisabledError):
        launcher.launch(LaunchRequest(plan=plan))


def test_m026_decision_flags_remain_false():
    record = LambdaRealLaunchDecisionRecord(
        status="approve_m027_minimal_real_mutation_implementation",
        rationale="implementation only",
    )

    assert record.real_mutation_enabled is False
    assert record.launch_ready is False
    assert record.launch_allowed is False
