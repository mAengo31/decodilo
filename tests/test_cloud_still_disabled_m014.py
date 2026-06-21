from decodilo.cloud.disabled_launcher import DisabledCloudLauncher
from decodilo.cloud.launch_plan import CloudLaunchPlan
from decodilo.cloud.launcher_interface import LaunchRequest
from decodilo.errors import LaunchDisabledError


def test_disabled_cloud_launcher_still_cannot_launch() -> None:
    launcher = DisabledCloudLauncher()
    plan = CloudLaunchPlan(
        run_id="cloud-disabled-m014",
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
        safety_buffer_adjusted_cost=1.0,
        max_run_budget=10.0,
        starting_credits=100.0,
        projected_remaining_credits=99.0,
        launch_allowed=False,
    )
    try:
        launcher.launch(LaunchRequest(plan=plan))
    except LaunchDisabledError as exc:
        assert "disabled" in str(exc).lower()
    else:  # pragma: no cover - should be impossible
        raise AssertionError("disabled launcher unexpectedly launched")
