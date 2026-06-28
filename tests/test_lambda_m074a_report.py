from decodilo.lambda_cloud.m074a_report import build_lambda_m074a_report_from_paths
from decodilo.lambda_cloud.m075r_runtime_protocol_smoke_authorization import (
    build_lambda_m075r_runtime_protocol_smoke_authorization_from_paths,
    write_lambda_m075r_runtime_protocol_smoke_authorization,
)
from decodilo.lambda_cloud.m075r_runtime_protocol_smoke_runbook_preview import (
    build_lambda_m075r_runtime_protocol_smoke_runbook_preview_from_path,
    write_lambda_m075r_runtime_protocol_smoke_runbook_preview,
)
from decodilo.lambda_cloud.runtime_protocol_smoke_discovery import (
    LambdaRuntimeProtocolSmokeDiscovery,
    write_lambda_runtime_protocol_smoke_discovery,
)
from decodilo.lambda_cloud.runtime_protocol_smoke_policy import (
    build_lambda_runtime_protocol_smoke_policy_from_path,
    write_lambda_runtime_protocol_smoke_policy,
)
from decodilo.lambda_cloud.runtime_protocol_smoke_readiness import (
    LambdaRuntimeProtocolSmokeReadiness,
    write_lambda_runtime_protocol_smoke_readiness,
)
from decodilo.lambda_cloud.tiny_smoke_closeout import (
    LambdaTinySmokeCloseout,
    write_lambda_tiny_smoke_closeout,
)


def test_m074a_report_passes_for_future_authorized_runtime_smoke(tmp_path):
    closeout_path = tmp_path / "closeout.json"
    readiness_path = tmp_path / "readiness.json"
    discovery_path = tmp_path / "discovery.json"
    policy_path = tmp_path / "policy.json"
    auth_path = tmp_path / "auth.json"
    runbook_path = tmp_path / "runbook.json"
    write_lambda_tiny_smoke_closeout(
        closeout_path,
        LambdaTinySmokeCloseout(
            closeout_status="closed_with_warnings",
            closeout_succeeded=True,
            tiny_smoke_success=True,
            reconciliation_passed=True,
            evidence_complete=True,
            artifact_auditable=True,
            termination_verified=True,
            no_internet_install=True,
            no_downloads=True,
            no_real_training=True,
            no_unapproved_file_transfer=True,
            historical_billable_action_performed=True,
        ),
    )
    write_lambda_runtime_protocol_smoke_readiness(
        readiness_path,
        LambdaRuntimeProtocolSmokeReadiness(
            readiness_status="ready_for_future_runtime_protocol_smoke_planning",
            cloud_lifecycle_ready=True,
            ssh_ready=True,
            source_bundle_ready=True,
            dependency_bundle_ready=True,
            decodilo_cli_ready=True,
            tiny_smoke_ready=True,
        ),
    )
    write_lambda_runtime_protocol_smoke_discovery(
        discovery_path,
        LambdaRuntimeProtocolSmokeDiscovery(
            discovery_status="found_safe_runtime_protocol_smoke_command",
            command_category="dev_runtime_smoke_synthetic",
            argv_tokens=["python3", "-m", "decodilo.cli", "dev", "runtime-smoke"],
            timeout_seconds=60,
        ),
    )
    write_lambda_runtime_protocol_smoke_policy(
        policy_path,
        build_lambda_runtime_protocol_smoke_policy_from_path(
            command_discovery=discovery_path,
        ),
    )
    write_lambda_m075r_runtime_protocol_smoke_authorization(
        auth_path,
        build_lambda_m075r_runtime_protocol_smoke_authorization_from_paths(
            tiny_smoke_closeout=closeout_path,
            readiness=readiness_path,
            command_discovery=discovery_path,
            policy=policy_path,
        ),
    )
    write_lambda_m075r_runtime_protocol_smoke_runbook_preview(
        runbook_path,
        build_lambda_m075r_runtime_protocol_smoke_runbook_preview_from_path(
            authorization=auth_path,
        ),
    )

    report = build_lambda_m074a_report_from_paths(
        runtime_discovery=discovery_path,
        runtime_policy=policy_path,
        authorization=auth_path,
        runbook_preview=runbook_path,
    )

    assert report.report_passed is True
    assert report.runtime_smoke_command_added is True
    assert report.m075r_authorization_status == (
        "authorized_for_future_m075r_runtime_protocol_smoke"
    )
    assert report.launch_ready is False
    assert report.launch_allowed is False
