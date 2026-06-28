from __future__ import annotations

from lambda_m072_helpers import make_m071r_workdir

from decodilo.lambda_cloud.first_experiment_success_record import (
    build_lambda_first_experiment_success_record_from_paths,
    write_lambda_first_experiment_success_record,
)
from decodilo.lambda_cloud.remote_artifact_audit import (
    build_lambda_remote_artifact_audit_from_paths,
)


def test_remote_artifact_audit_passes_metadata_capture(tmp_path):
    workdir = make_m071r_workdir(tmp_path)
    success_path = tmp_path / "success.json"
    write_lambda_first_experiment_success_record(
        success_path,
        build_lambda_first_experiment_success_record_from_paths(workdir=workdir),
    )

    audit = build_lambda_remote_artifact_audit_from_paths(
        workdir=workdir,
        success_record=success_path,
    )

    assert audit.artifact_audit_passed is True
    assert audit.secret_scan_passed is True
    assert audit.launch_ready is False
    assert audit.launch_allowed is False
