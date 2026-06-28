from __future__ import annotations

from lambda_m080_helpers import make_m079r2_workdir, write_m080_closeout_chain

from decodilo.lambda_cloud.learner_syncer_smoke_reconciliation import (
    build_lambda_learner_syncer_smoke_reconciliation_from_paths,
)


def test_learner_syncer_reconciliation_passes_for_clean_m079r2(tmp_path):
    workdir = make_m079r2_workdir(tmp_path)
    paths = write_m080_closeout_chain(tmp_path, workdir)

    report = build_lambda_learner_syncer_smoke_reconciliation_from_paths(
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
    assert report.launch_ready is False
    assert report.launch_allowed is False
