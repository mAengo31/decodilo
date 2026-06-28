from __future__ import annotations

from lambda_m082_helpers import make_m081r2_workdir, write_m082_closeout_chain

from decodilo.lambda_cloud.diloco_synthetic_reconciliation import (
    build_lambda_diloco_synthetic_reconciliation_from_paths,
)


def test_diloco_synthetic_reconciliation_passes_for_m081r2(tmp_path):
    workdir = make_m081r2_workdir(tmp_path)
    paths = write_m082_closeout_chain(tmp_path, workdir)

    report = build_lambda_diloco_synthetic_reconciliation_from_paths(
        workdir=workdir,
        success_record=paths["success"],
    )

    assert report.reconciliation_passed is True
    assert report.optimizer_claim_honesty_confirmed is True
    assert report.no_training is True
    assert report.no_downloads is True
    assert report.no_internet_install is True
    assert report.launch_ready is False
    assert report.launch_allowed is False
