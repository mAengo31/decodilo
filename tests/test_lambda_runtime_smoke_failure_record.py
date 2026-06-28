from __future__ import annotations

from lambda_m075s_helpers import make_m075r_runtime_smoke_failure_workdir

from decodilo.lambda_cloud.runtime_smoke_failure_record import (
    build_lambda_runtime_smoke_failure_record_from_paths,
)


def test_runtime_smoke_failure_record_classifies_m075r_failure(tmp_path):
    workdir = make_m075r_runtime_smoke_failure_workdir(tmp_path)

    record = build_lambda_runtime_smoke_failure_record_from_paths(workdir=workdir)

    assert record.failure_status == "runtime_smoke_command_failed"
    assert record.infrastructure_passed is True
    assert record.source_upload_passed is True
    assert record.dependency_upload_passed is True
    assert record.dependency_install_passed is True
    assert record.decodilo_import_passed is True
    assert record.cli_help_passed is True
    assert record.runtime_smoke_attempted is True
    assert record.runtime_smoke_exit_code == 1
    assert record.stderr_empty is True
    assert record.stdout_redacted_hash_present is True
    assert record.expected_artifact_metadata_captured is False
    assert record.failure_diagnosis_status == "insufficient_failure_artifact_evidence"
    assert record.no_internet_install is True
    assert record.no_downloads is True
    assert record.no_training is True
    assert record.termination_verified is True
    assert record.final_instance_count == 0
    assert record.final_unmanaged_count == 0
    assert record.launch_ready is False
    assert record.launch_allowed is False
