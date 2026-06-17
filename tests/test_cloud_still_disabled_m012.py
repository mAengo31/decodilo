import pytest

from decodilo.cloud.disabled_launcher import DisabledCloudLauncher
from decodilo.cloud.launch_plan import CloudLaunchPlan
from decodilo.cloud.launcher_interface import LaunchRequest
from decodilo.errors import LaunchDisabledError

pytestmark = pytest.mark.cloud_disabled


def test_disabled_launcher_still_cannot_launch() -> None:
    plan = CloudLaunchPlan(
        run_id="run-disabled",
        provider="lambda",
        node_count=1,
        instance_type="planning-only",
        gpu_type="H100 SXM",
        gpus_per_instance=8,
        total_gpus=8,
        planned_hours=1.0,
        price_snapshot_id="snapshot",
        selected_price_record_id="record",
        base_estimated_cost=1.0,
        safety_buffer_adjusted_cost=1.15,
        max_run_budget=10.0,
        starting_credits=100.0,
        projected_remaining_credits=98.85,
        launch_allowed=False,
    )
    with pytest.raises(LaunchDisabledError):
        DisabledCloudLauncher().launch(LaunchRequest(plan=plan))
