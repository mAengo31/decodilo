from __future__ import annotations

from lambda_m072_helpers import make_m071r_workdir

from decodilo.lambda_cloud.first_experiment_evidence_package import (
    build_lambda_first_experiment_evidence_package_from_paths,
)
from decodilo.lambda_cloud.first_experiment_reconciliation import (
    build_lambda_first_experiment_reconciliation_from_paths,
    write_lambda_first_experiment_reconciliation,
)
from decodilo.lambda_cloud.first_experiment_success_record import (
    build_lambda_first_experiment_success_record_from_paths,
    write_lambda_first_experiment_success_record,
)


def test_first_experiment_evidence_package_is_complete(tmp_path):
    workdir = make_m071r_workdir(tmp_path)
    success_path = tmp_path / "success.json"
    reconciliation_path = tmp_path / "reconciliation.json"
    write_lambda_first_experiment_success_record(
        success_path,
        build_lambda_first_experiment_success_record_from_paths(workdir=workdir),
    )
    write_lambda_first_experiment_reconciliation(
        reconciliation_path,
        build_lambda_first_experiment_reconciliation_from_paths(
            workdir=workdir,
            success_record=success_path,
        ),
    )

    package = build_lambda_first_experiment_evidence_package_from_paths(
        success_record=success_path,
        reconciliation=reconciliation_path,
    )

    assert package.evidence_complete is True
    assert package.first_experiment_success is True
    assert package.launch_ready is False
    assert package.launch_allowed is False
