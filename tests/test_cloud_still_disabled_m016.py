import pytest

from decodilo.cloud.disabled_launcher import DisabledCloudLauncher
from decodilo.cloud.launch_plan import CloudLaunchPlan
from decodilo.cloud.launcher_interface import LaunchRequest
from decodilo.errors import LaunchDisabledError
from decodilo.storage.disabled_remote_backend import (
    DisabledRemoteArtifactBackend,
    RemoteBackendDisabledError,
)
from decodilo.storage.remote_backend_conformance import (
    passing_simulator_config,
    run_remote_backend_conformance_suite,
)
from decodilo.storage.remote_backend_requirements import RemoteBackendRequirementSet


def test_cloud_launcher_still_disabled() -> None:
    launcher = DisabledCloudLauncher()
    request = LaunchRequest(
        plan=CloudLaunchPlan(
            run_id="m016",
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


def test_disabled_remote_backend_still_raises() -> None:
    backend = DisabledRemoteArtifactBackend()

    assert backend.remote_capabilities().remote_backend_enabled is False
    with pytest.raises(RemoteBackendDisabledError):
        backend.write_bytes(artifact_id="x", data=b"x")


def test_simulator_conformance_does_not_enable_remote_or_launch() -> None:
    requirements = RemoteBackendRequirementSet(
        scenario_id="m016-cloud-disabled",
        target_learner_count=2,
        stress_learner_count=4,
        peak_artifact_read_gbps=1,
        peak_artifact_write_gbps=1,
        peak_artifact_ops_per_second=10,
        peak_syncer_merge_gbps=1,
        checkpoint_storage_growth_gb_per_hour=1,
        event_log_growth_mb_per_hour=1,
        required_replay_snapshot_frequency="every checkpoint",
    )
    report = run_remote_backend_conformance_suite(
        requirements=requirements,
        simulator_config=passing_simulator_config(requirements),
    )

    assert report.passed is True
    assert report.remote_backend_enabled is False
    assert report.launch_ready is False
    assert report.launch_allowed is False
