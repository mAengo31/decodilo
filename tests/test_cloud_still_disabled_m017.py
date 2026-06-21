import pytest

from decodilo.cloud.disabled_launcher import DisabledCloudLauncher
from decodilo.cloud.launch_plan import CloudLaunchPlan
from decodilo.cloud.launcher_interface import LaunchRequest
from decodilo.errors import LaunchDisabledError
from decodilo.storage.disabled_remote_backend import (
    DisabledRemoteArtifactBackend,
    RemoteBackendDisabledError,
)
from decodilo.storage.remote_backend_decision_record import (
    RemoteBackendDecisionRecord,
    RemoteBackendDecisionStatus,
)


def test_cloud_launcher_remains_disabled_m017() -> None:
    launcher = DisabledCloudLauncher()
    request = LaunchRequest(
        plan=CloudLaunchPlan(
            run_id="m017",
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


def test_remote_backend_remains_disabled_m017() -> None:
    backend = DisabledRemoteArtifactBackend()

    with pytest.raises(RemoteBackendDisabledError):
        backend.read_bytes(None)  # type: ignore[arg-type]


def test_decision_record_cannot_emit_enabled_statuses() -> None:
    with pytest.raises(ValueError):
        RemoteBackendDecisionRecord(
            decision_id="bad",
            proposal_ref="proposal.json",
            evidence_package_ref="evidence.json",
            readiness_report_ref="readiness.json",
            risk_register_ref="risk.json",
            sdk_guard_report_ref="guard.json",
            status=RemoteBackendDecisionStatus.real_backend_enabled,
            rationale="bad",
        )
