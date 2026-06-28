from __future__ import annotations

from lambda_m084_helpers import make_m083r_workdir, write_m084_optimizer_closeout_chain

from decodilo.lambda_cloud.diloco_optimizer_reconciliation import (
    build_lambda_diloco_optimizer_reconciliation_from_paths,
)


def test_diloco_optimizer_reconciliation_passes_for_success_record(tmp_path):
    workdir = make_m083r_workdir(tmp_path)
    paths = write_m084_optimizer_closeout_chain(tmp_path, workdir)

    report = build_lambda_diloco_optimizer_reconciliation_from_paths(
        workdir=workdir,
        success_record=paths["success"],
    )

    assert report.reconciliation_passed is True
    assert report.no_unapproved_file_transfer is True
    assert report.no_training is True
    assert report.no_downloads is True
    assert report.no_internet_install is True
    assert report.optimizer_semantics_confirmed is True
    assert report.termination_verified is True
    assert report.launch_ready is False
    assert report.launch_allowed is False
