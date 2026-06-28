from __future__ import annotations

from lambda_m090_helpers import make_m089r_workdir, write_m090_bounded_closeout_chain

from decodilo.lambda_cloud.bounded_diloco_experiment_evidence_package import (
    build_lambda_bounded_diloco_experiment_evidence_package_from_paths,
)


def test_bounded_diloco_experiment_evidence_package_complete(tmp_path):
    paths = write_m090_bounded_closeout_chain(
        tmp_path,
        make_m089r_workdir(tmp_path),
    )

    report = build_lambda_bounded_diloco_experiment_evidence_package_from_paths(
        success_record=paths["success"],
        reconciliation=paths["reconciliation"],
    )

    assert report.evidence_complete is True
    assert report.bounded_diloco_experiment_success is True
    assert report.reconciliation_passed is True
    assert report.bounded_experiment_semantics_confirmed is True
    assert report.launch_ready is False
    assert report.launch_allowed is False
