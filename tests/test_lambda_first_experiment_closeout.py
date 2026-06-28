from __future__ import annotations

from decodilo.lambda_cloud.first_experiment_closeout import (
    LambdaFirstExperimentCloseout,
    build_lambda_first_experiment_closeout_from_paths,
)
from decodilo.lambda_cloud.first_experiment_evidence_package import (
    LambdaFirstExperimentEvidencePackage,
    write_lambda_first_experiment_evidence_package,
)
from decodilo.lambda_cloud.first_experiment_reconciliation import (
    LambdaFirstExperimentReconciliation,
    write_lambda_first_experiment_reconciliation,
)
from decodilo.lambda_cloud.first_experiment_success_record import (
    LambdaFirstExperimentSuccessRecord,
    write_lambda_first_experiment_success_record,
)


def test_first_experiment_closeout_succeeds_clean_chain(tmp_path):
    success = tmp_path / "success.json"
    reconciliation = tmp_path / "reconciliation.json"
    evidence = tmp_path / "evidence.json"
    write_lambda_first_experiment_success_record(success, _success_record())
    write_lambda_first_experiment_reconciliation(
        reconciliation,
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
    write_lambda_first_experiment_evidence_package(
        evidence,
        LambdaFirstExperimentEvidencePackage(
            evidence_complete=True,
            first_experiment_success=True,
            reconciliation_passed=True,
        ),
    )

    closeout = build_lambda_first_experiment_closeout_from_paths(
        success_record=success,
        reconciliation=reconciliation,
        evidence_package=evidence,
    )

    assert closeout.closeout_succeeded is True
    assert closeout.closeout_status in {"closed_success", "closed_with_warnings"}
    assert closeout.launch_ready is False
    assert closeout.launch_allowed is False


def test_first_experiment_closeout_blocks_training() -> None:
    closeout = LambdaFirstExperimentCloseout(
        closeout_status="unresolved",
        closeout_succeeded=False,
        first_experiment_runtime_success=False,
        reconciliation_passed=False,
        evidence_complete=False,
        artifact_auditable=True,
        termination_verified=True,
        no_internet_install=True,
        no_downloads=True,
        no_training=False,
        no_unapproved_file_transfer=True,
        historical_billable_action_performed=True,
        blockers=["training_detected"],
    )

    assert closeout.closeout_succeeded is False
    assert closeout.launch_ready is False
    assert closeout.launch_allowed is False


def _success_record() -> LambdaFirstExperimentSuccessRecord:
    return LambdaFirstExperimentSuccessRecord(
        status="first_experiment_runtime_success",
        source_upload_passed=True,
        dependency_upload_passed=True,
        source_hash_verification_passed=True,
        dependency_hash_verification_passed=True,
        local_only_dependency_install_passed=True,
        decodilo_import_passed=True,
        cli_help_passed=True,
        first_experiment_command_passed=True,
        ci_profile_report_artifact_created=True,
        artifact_secret_scan_passed=True,
        artifact_bounded=True,
        no_internet_install=True,
        no_downloads=True,
        no_training=True,
        no_unapproved_file_transfer=True,
        no_port_forwarding=True,
        termination_verified=True,
        final_instance_count=0,
        final_unmanaged_count=0,
        manual_review_required=False,
        historical_billable_action_performed=True,
        spend_under_budget=True,
        secret_scan_passed=True,
    )
