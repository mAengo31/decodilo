from __future__ import annotations

from lambda_m088_helpers import make_m087r_workdir, write_m088_parameter_fragment_closeout_chain

from decodilo.lambda_cloud.parameter_fragment_reconciliation import (
    build_lambda_parameter_fragment_reconciliation_from_paths,
)


def test_parameter_fragment_reconciliation_passes_clean_m087r_evidence(tmp_path):
    workdir = make_m087r_workdir(tmp_path)
    paths = write_m088_parameter_fragment_closeout_chain(tmp_path, workdir)

    report = build_lambda_parameter_fragment_reconciliation_from_paths(
        workdir=workdir,
        success_record=paths["success"],
    )

    assert report.reconciliation_passed is True
    assert report.no_unapproved_file_transfer is True
    assert report.no_training is True
    assert report.no_downloads is True
    assert report.no_internet_install is True
    assert report.fragment_semantics_confirmed is True
    assert report.termination_verified is True
    assert report.launch_ready is False
    assert report.launch_allowed is False
