from __future__ import annotations

from lambda_m078_helpers import make_m077r_workdir, write_m078_closeout_chain

from decodilo.lambda_cloud.synthetic_experiment_reconciliation import (
    build_lambda_synthetic_experiment_reconciliation_from_paths,
)


def test_synthetic_experiment_reconciliation_passes_m077r_success(tmp_path):
    workdir = make_m077r_workdir(tmp_path)
    paths = write_m078_closeout_chain(tmp_path, workdir)

    report = build_lambda_synthetic_experiment_reconciliation_from_paths(
        workdir=workdir,
        success_record=paths["success"],
    )

    assert report.reconciliation_passed is True
    assert report.no_unapproved_file_transfer is True
    assert report.no_training is True
    assert report.no_downloads is True
    assert report.no_internet_install is True
    assert report.launch_ready is False
    assert report.launch_allowed is False
