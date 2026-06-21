import pytest

from decodilo.cloud.disabled_launcher import DisabledCloudLauncher
from decodilo.cloud.launch_plan import CloudLaunchPlan
from decodilo.cloud.launcher_interface import LaunchRequest
from decodilo.errors import LaunchDisabledError
from decodilo.lambda_cloud.live_discovery_report import LambdaLiveDiscoveryReport


def test_cloud_launcher_remains_disabled_m019() -> None:
    launcher = DisabledCloudLauncher()
    request = LaunchRequest(
        plan=CloudLaunchPlan(
            run_id="m019",
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


def test_live_discovery_report_is_non_launchable() -> None:
    report = LambdaLiveDiscoveryReport(live_api_used=True)

    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.billable_action_performed is False
