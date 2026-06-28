from __future__ import annotations

from lambda_m076_helpers import make_m075r4_workdir, write_m076_closeout_chain

from decodilo.lambda_cloud.runtime_smoke_reconciliation import (
    build_lambda_runtime_smoke_reconciliation_from_paths,
)


def test_runtime_smoke_reconciliation_passes_m075r4_success(tmp_path):
    workdir = make_m075r4_workdir(tmp_path)
    paths = write_m076_closeout_chain(tmp_path, workdir)

    report = build_lambda_runtime_smoke_reconciliation_from_paths(
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
