from __future__ import annotations

from lambda_m090_helpers import make_m089r_workdir, write_m090_bounded_closeout_chain

from decodilo.lambda_cloud.bounded_diloco_experiment_reconciliation import (
    build_lambda_bounded_diloco_experiment_reconciliation_from_paths,
)


def test_bounded_diloco_experiment_reconciliation_passes(tmp_path):
    workdir = make_m089r_workdir(tmp_path)
    paths = write_m090_bounded_closeout_chain(tmp_path, workdir)

    report = build_lambda_bounded_diloco_experiment_reconciliation_from_paths(
        workdir=workdir,
        success_record=paths["success"],
    )

    assert report.reconciliation_passed is True
    assert report.final_instance_count == 0
    assert report.final_unmanaged_count == 0
    assert report.no_unapproved_file_transfer is True
    assert report.no_training is True
    assert report.no_downloads is True
    assert report.no_internet_install is True
    assert report.bounded_experiment_semantics_confirmed is True
    assert report.launch_ready is False
    assert report.launch_allowed is False
