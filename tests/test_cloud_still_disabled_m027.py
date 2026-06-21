import pytest

from decodilo.cloud.disabled_launcher import DisabledCloudLauncher
from decodilo.cloud.launch_plan import CloudLaunchPlan
from decodilo.cloud.launcher_interface import LaunchRequest
from decodilo.errors import LaunchDisabledError


def test_cloud_launcher_still_disabled_m027():
    plan = CloudLaunchPlan(
        run_id="m027",
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
