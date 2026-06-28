from __future__ import annotations

from lambda_m078_helpers import make_m077r_workdir, write_m078_closeout_chain

from decodilo.lambda_cloud.synthetic_experiment_evidence_package import (
    build_lambda_synthetic_experiment_evidence_package_from_paths,
)


def test_synthetic_experiment_evidence_package_complete(tmp_path):
    workdir = make_m077r_workdir(tmp_path)
    paths = write_m078_closeout_chain(tmp_path, workdir)

    package = build_lambda_synthetic_experiment_evidence_package_from_paths(
        success_record=paths["success"],
        reconciliation=paths["reconciliation"],
    )

    assert package.evidence_complete is True
    assert package.synthetic_experiment_success is True
    assert package.reconciliation_passed is True
    assert package.launch_ready is False
    assert package.launch_allowed is False
