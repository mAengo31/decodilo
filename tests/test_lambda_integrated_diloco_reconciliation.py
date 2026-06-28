from __future__ import annotations

from lambda_m086_helpers import make_m085r_workdir

from decodilo.lambda_cloud.integrated_diloco_reconciliation import (
    build_lambda_integrated_diloco_reconciliation_from_paths,
)
from decodilo.lambda_cloud.integrated_diloco_success_record import (
    build_lambda_integrated_diloco_success_record_from_paths,
    write_lambda_integrated_diloco_success_record,
)


def test_integrated_diloco_reconciliation_passes(tmp_path):
    workdir = make_m085r_workdir(tmp_path)
    success_path = tmp_path / "success.json"
    write_lambda_integrated_diloco_success_record(
        success_path,
        build_lambda_integrated_diloco_success_record_from_paths(workdir=workdir),
    )

    report = build_lambda_integrated_diloco_reconciliation_from_paths(
        workdir=workdir,
        success_record=success_path,
    )

    assert report.reconciliation_passed is True
    assert report.no_unapproved_file_transfer is True
    assert report.no_training is True
    assert report.integrated_semantics_confirmed is True
    assert report.launch_ready is False
    assert report.launch_allowed is False
