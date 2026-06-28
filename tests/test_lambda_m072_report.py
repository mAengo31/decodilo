from __future__ import annotations

from test_lambda_first_experiment_closeout import _success_record

from decodilo.lambda_cloud.first_experiment_closeout import (
    LambdaFirstExperimentCloseout,
    write_lambda_first_experiment_closeout,
)
from decodilo.lambda_cloud.first_experiment_reconciliation import (
    LambdaFirstExperimentReconciliation,
    write_lambda_first_experiment_reconciliation,
)
from decodilo.lambda_cloud.first_experiment_success_record import (
    write_lambda_first_experiment_success_record,
)
from decodilo.lambda_cloud.m072_report import build_lambda_m072_report_from_paths
from decodilo.lambda_cloud.m073r_tiny_smoke_authorization import (
    LambdaM073RTinySmokeAuthorization,
    write_lambda_m073r_tiny_smoke_authorization,
)
from decodilo.lambda_cloud.m073r_tiny_smoke_runbook_preview import (
    LambdaM073RTinySmokeRunbookPreview,
    write_lambda_m073r_tiny_smoke_runbook_preview,
)
from decodilo.lambda_cloud.remote_artifact_audit import (
    LambdaRemoteArtifactAudit,
    write_lambda_remote_artifact_audit,
)
from decodilo.lambda_cloud.tiny_decodilo_smoke_discovery import (
    LambdaTinyDecodiloSmokeDiscovery,
    write_lambda_tiny_decodilo_smoke_discovery,
)
from decodilo.lambda_cloud.tiny_decodilo_smoke_policy import (
    LambdaTinyDecodiloSmokePolicy,
    write_lambda_tiny_decodilo_smoke_policy,
)


def test_m072_report_records_not_authorized_smoke_blocker(tmp_path):
    paths = {name: tmp_path / f"{name}.json" for name in _M072_PATH_NAMES}
    write_lambda_first_experiment_success_record(paths["success"], _success_record())
    write_lambda_first_experiment_reconciliation(
        paths["reconciliation"],
        LambdaFirstExperimentReconciliation(
            reconciliation_passed=True,
            final_instance_count=0,
            final_unmanaged_count=0,
            no_unapproved_file_transfer=True,
            no_training=True,
            no_downloads=True,
            no_internet_install=True,
            local_only_dependency_install_confirmed=True,
            first_experiment_command_passed=True,
            artifact_metadata_confirmed=True,
            termination_verified=True,
        ),
    )
    write_lambda_first_experiment_closeout(
        paths["closeout"],
        LambdaFirstExperimentCloseout(
            closeout_status="closed_success",
            closeout_succeeded=True,
            first_experiment_runtime_success=True,
            reconciliation_passed=True,
            evidence_complete=True,
            artifact_auditable=True,
            termination_verified=True,
            no_internet_install=True,
            no_downloads=True,
            no_training=True,
            no_unapproved_file_transfer=True,
            historical_billable_action_performed=True,
        ),
    )
    write_lambda_remote_artifact_audit(
        paths["artifact"],
        LambdaRemoteArtifactAudit(
            artifact_audit_passed=True,
            artifact_type_expected=True,
            artifact_bounded=True,
            secret_scan_passed=True,
            no_raw_secrets=True,
        ),
    )
    write_lambda_tiny_decodilo_smoke_discovery(
        paths["discovery"],
        LambdaTinyDecodiloSmokeDiscovery(
            discovery_status="no_safe_tiny_smoke_command_found",
            blockers=["no_safe_tiny_smoke_command_found"],
        ),
    )
    write_lambda_tiny_decodilo_smoke_policy(
        paths["policy"],
        LambdaTinyDecodiloSmokePolicy(
            policy_status="blocked_no_safe_command",
            one_tiny_decodilo_smoke_command=False,
            bounded_timeout=False,
            bounded_output=False,
            blockers=["no_safe_tiny_smoke_command_found"],
        ),
    )
    write_lambda_m073r_tiny_smoke_authorization(
        paths["authorization"],
        LambdaM073RTinySmokeAuthorization(
            authorization_status="not_authorized",
            blockers=["no_safe_tiny_smoke_command_found"],
        ),
    )
    write_lambda_m073r_tiny_smoke_runbook_preview(
        paths["preview"],
        LambdaM073RTinySmokeRunbookPreview(
            preview_status="blocked_no_safe_tiny_smoke_command",
            blockers=["no_safe_tiny_smoke_command_found"],
        ),
    )

    report = build_lambda_m072_report_from_paths(
        success_record=paths["success"],
        reconciliation=paths["reconciliation"],
        closeout=paths["closeout"],
        artifact_audit=paths["artifact"],
        smoke_discovery=paths["discovery"],
        smoke_policy=paths["policy"],
        authorization=paths["authorization"],
        runbook_preview=paths["preview"],
    )

    assert report.report_passed is True
    assert report.m073r_authorization_status == "not_authorized"
    assert "no_safe_tiny_smoke_command_found" in report.m073r_blockers
    assert report.blockers == []
    assert report.launch_ready is False
    assert report.launch_allowed is False


_M072_PATH_NAMES = (
    "success",
    "reconciliation",
    "closeout",
    "artifact",
    "discovery",
    "policy",
    "authorization",
    "preview",
)
