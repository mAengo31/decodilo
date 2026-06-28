from lambda_m074_helpers import make_m073r2_workdir

from decodilo.lambda_cloud.tiny_smoke_artifact_audit import (
    build_lambda_tiny_smoke_artifact_audit_from_paths,
)
from decodilo.lambda_cloud.tiny_smoke_success_record import (
    build_lambda_tiny_smoke_success_record_from_paths,
    write_lambda_tiny_smoke_success_record,
)


def test_tiny_smoke_artifact_audit_accepts_metadata_only_artifact(tmp_path):
    workdir = make_m073r2_workdir(tmp_path)
    success_path = tmp_path / "success.json"
    write_lambda_tiny_smoke_success_record(
        success_path,
        build_lambda_tiny_smoke_success_record_from_paths(workdir=workdir),
    )

    audit = build_lambda_tiny_smoke_artifact_audit_from_paths(
        workdir=workdir,
        success_record=success_path,
    )

    assert audit.artifact_audit_passed is True
    assert audit.artifact_type == "JSON"
    assert audit.smoke_status == "passed"
    assert audit.metadata_only is True
    assert audit.launch_ready is False
    assert audit.launch_allowed is False
