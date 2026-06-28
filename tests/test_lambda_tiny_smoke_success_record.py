from lambda_m074_helpers import make_m073r2_workdir

from decodilo.lambda_cloud.tiny_smoke_success_record import (
    M073R2_TINY_SMOKE_ARTIFACT_SHA256,
    build_lambda_tiny_smoke_success_record_from_paths,
)


def test_tiny_smoke_success_record_closes_successful_m073r2(tmp_path):
    workdir = make_m073r2_workdir(tmp_path)

    record = build_lambda_tiny_smoke_success_record_from_paths(workdir=workdir)

    assert record.status == "tiny_smoke_success"
    assert record.source_upload_passed is True
    assert record.dependency_upload_passed is True
    assert record.local_only_dependency_install_passed is True
    assert record.decodilo_import_passed is True
    assert record.cli_help_passed is True
    assert record.tiny_smoke_command_passed is True
    assert record.artifact_sha256 == M073R2_TINY_SMOKE_ARTIFACT_SHA256
    assert record.no_internet_install is True
    assert record.no_downloads is True
    assert record.no_real_training is True
    assert record.termination_verified is True
    assert record.final_instance_count == 0
    assert record.final_unmanaged_count == 0
    assert record.launch_ready is False
    assert record.launch_allowed is False
    assert record.billable_action_performed is False
