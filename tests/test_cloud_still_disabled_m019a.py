import pytest

from decodilo.cloud.disabled_launcher import DisabledCloudLauncher
from decodilo.cloud.launch_plan import CloudLaunchPlan
from decodilo.cloud.launcher_interface import LaunchRequest
from decodilo.errors import LaunchDisabledError
from decodilo.lambda_cloud.live_discovery_report import LambdaLiveDiscoveryReport
from decodilo.lambda_cloud.preflight import LambdaPreflightReport


def test_cloud_launcher_remains_disabled_m019a() -> None:
    launcher = DisabledCloudLauncher()
    request = LaunchRequest(
        plan=CloudLaunchPlan(
            run_id="m019a",
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


def test_lambda_m019a_reports_are_non_launchable() -> None:
    discovery = LambdaLiveDiscoveryReport(live_api_used=True)
    preflight = LambdaPreflightReport(
        passed=True,
        preflight_status="passed_read_only",
        mutation_guard={},
    )

    assert discovery.launch_ready is False
    assert discovery.launch_allowed is False
    assert discovery.billable_action_performed is False
    assert preflight.launch_ready is False
    assert preflight.launch_allowed is False
