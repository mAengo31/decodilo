from __future__ import annotations

from decodilo.lambda_cloud.first_experiment_command_discovery import (
    LambdaFirstExperimentCommandDiscovery,
    write_lambda_first_experiment_command_discovery,
)
from decodilo.lambda_cloud.first_experiment_readiness import (
    LambdaFirstExperimentReadiness,
    write_lambda_first_experiment_readiness,
)
from decodilo.lambda_cloud.m070_report import build_lambda_m070_report_from_paths
from decodilo.lambda_cloud.m071r_first_experiment_authorization import (
    LambdaM071RFirstExperimentAuthorization,
    write_lambda_m071r_first_experiment_authorization,
)
from decodilo.lambda_cloud.m071r_first_experiment_runbook_preview import (
    LambdaM071RFirstExperimentRunbookPreview,
    write_lambda_m071r_first_experiment_runbook_preview,
)
from decodilo.lambda_cloud.remote_decodilo_vslice_closeout import (
    LambdaRemoteDecodiloVSliceCloseout,
    write_lambda_remote_decodilo_vslice_closeout,
)
from decodilo.lambda_cloud.remote_decodilo_vslice_reconciliation import (
    LambdaRemoteDecodiloVSliceReconciliation,
    write_lambda_remote_decodilo_vslice_reconciliation,
)
from decodilo.lambda_cloud.remote_decodilo_vslice_success_record import (
    LambdaRemoteDecodiloVSliceSuccessRecord,
    write_lambda_remote_decodilo_vslice_success_record,
)


def test_m070_report_passes_for_successful_chain(tmp_path):
    success = tmp_path / "success.json"
    reconciliation = tmp_path / "reconciliation.json"
    closeout = tmp_path / "closeout.json"
    readiness = tmp_path / "readiness.json"
    discovery = tmp_path / "discovery.json"
    auth = tmp_path / "auth.json"
    preview = tmp_path / "preview.json"
    write_lambda_remote_decodilo_vslice_success_record(
        success,
        LambdaRemoteDecodiloVSliceSuccessRecord(
            status="remote_decodilo_vslice_success",
            source_upload_passed=True,
            dependency_upload_passed=True,
            source_hash_verification_passed=True,
            dependency_hash_verification_passed=True,
            local_only_dependency_install_passed=True,
            decodilo_import_passed=True,
            cli_help_passed=True,
            profile_summary_passed=True,
            ci_profile_smoke_passed=True,
            no_internet_install=True,
            no_downloads=True,
            no_training=True,
            no_extra_file_transfer=True,
            no_port_forwarding=True,
            termination_verified=True,
            final_instance_count=0,
            final_unmanaged_count=0,
            manual_review_required=False,
            historical_billable_action_performed=True,
            spend_under_budget=True,
            secret_scan_passed=True,
        ),
    )
    write_lambda_remote_decodilo_vslice_reconciliation(
        reconciliation,
        LambdaRemoteDecodiloVSliceReconciliation(
            reconciliation_passed=True,
            final_instance_count=0,
            final_unmanaged_count=0,
            no_unapproved_file_transfer=True,
            no_training=True,
            no_downloads=True,
            no_internet_install=True,
            local_only_dependency_install_confirmed=True,
            all_remote_vslice_stages_passed=True,
            termination_verified=True,
        ),
    )
    write_lambda_remote_decodilo_vslice_closeout(
        closeout,
        LambdaRemoteDecodiloVSliceCloseout(
            closeout_status="closed_success",
            closeout_succeeded=True,
            remote_decodilo_vslice_success=True,
            reconciliation_passed=True,
            evidence_complete=True,
            termination_verified=True,
            no_internet_install=True,
            no_downloads=True,
            no_training=True,
            no_extra_file_transfer=True,
            historical_billable_action_performed=True,
        ),
    )
    write_lambda_first_experiment_readiness(
        readiness,
        LambdaFirstExperimentReadiness(
            readiness_status="ready_for_future_first_experiment_planning",
            cloud_lifecycle_ready=True,
            ssh_ready=True,
            source_upload_ready=True,
            dependency_bundle_ready=True,
            decodilo_cli_ready=True,
        ),
    )
    write_lambda_first_experiment_command_discovery(
        discovery,
        LambdaFirstExperimentCommandDiscovery(
            discovery_status="safe_experiment_command_found",
            argv_tokens=["python3", "-m", "decodilo.cli", "dev", "ci-profile-report"],
        ),
    )
    write_lambda_m071r_first_experiment_authorization(
        auth,
        LambdaM071RFirstExperimentAuthorization(
            authorization_status="authorized_for_future_m071r_first_experiment_attempt",
        ),
    )
    write_lambda_m071r_first_experiment_runbook_preview(
        preview,
        LambdaM071RFirstExperimentRunbookPreview(
            preview_status="ready_for_future_m071r_first_experiment_review",
        ),
    )

    report = build_lambda_m070_report_from_paths(
        success_record=success,
        reconciliation=reconciliation,
        closeout=closeout,
        readiness=readiness,
        command_discovery=discovery,
        authorization=auth,
        runbook_preview=preview,
    )

    assert report.report_passed is True
    assert report.historical_billable_action_performed is True
    assert report.billable_action_performed is False
    assert report.launch_ready is False
    assert report.launch_allowed is False
