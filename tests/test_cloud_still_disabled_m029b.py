import pytest

from decodilo.cloud.disabled_launcher import DisabledCloudLauncher
from decodilo.cloud.launch_plan import CloudLaunchPlan
from decodilo.cloud.launcher_interface import LaunchRequest
from decodilo.errors import LaunchDisabledError


def test_cloud_launcher_still_disabled_m029b():
    plan = CloudLaunchPlan(
        run_id="m029b",
        provider="lambda",
        node_count=1,
        instance_type="gpu_8x_h100_sxm",
        gpu_type="H100 SXM",
        gpus_per_instance=8,
        total_gpus=8,
        planned_hours=0.5,
        price_snapshot_id="snapshot",
        selected_price_record_id="record",
        base_estimated_cost=15.96,
        safety_buffer_adjusted_cost=18.354,
        max_run_budget=50,
        starting_credits=100,
        projected_remaining_credits=81.646,
        launch_allowed=False,
    )

    with pytest.raises(LaunchDisabledError):
        DisabledCloudLauncher().launch(LaunchRequest(plan=plan))
