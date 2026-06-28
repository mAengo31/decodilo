from lambda_m074_helpers import make_m073r2_workdir

from decodilo.lambda_cloud.tiny_smoke_evidence_package import (
    build_lambda_tiny_smoke_evidence_package_from_paths,
)
from decodilo.lambda_cloud.tiny_smoke_reconciliation import (
    build_lambda_tiny_smoke_reconciliation_from_paths,
    write_lambda_tiny_smoke_reconciliation,
)
from decodilo.lambda_cloud.tiny_smoke_success_record import (
    build_lambda_tiny_smoke_success_record_from_paths,
    write_lambda_tiny_smoke_success_record,
)


def test_tiny_smoke_evidence_package_hashes_required_artifacts(tmp_path):
    workdir = make_m073r2_workdir(tmp_path)
    success_path = tmp_path / "success.json"
    reconciliation_path = tmp_path / "reconciliation.json"
    write_lambda_tiny_smoke_success_record(
        success_path,
        build_lambda_tiny_smoke_success_record_from_paths(workdir=workdir),
    )
    write_lambda_tiny_smoke_reconciliation(
        reconciliation_path,
        build_lambda_tiny_smoke_reconciliation_from_paths(
            workdir=workdir,
            success_record=success_path,
        ),
    )

    package = build_lambda_tiny_smoke_evidence_package_from_paths(
        success_record=success_path,
        reconciliation=reconciliation_path,
    )

    assert package.evidence_complete is True
    assert package.tiny_smoke_success is True
    assert package.reconciliation_passed is True
    assert "success_record" in package.artifact_hashes
    assert package.launch_ready is False
    assert package.launch_allowed is False
