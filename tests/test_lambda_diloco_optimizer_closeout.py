from __future__ import annotations

from lambda_m084_helpers import make_m083r_workdir, write_m084_optimizer_closeout_chain

from decodilo.lambda_cloud.diloco_optimizer_closeout import (
    build_lambda_diloco_optimizer_closeout_from_paths,
)


def test_diloco_optimizer_closeout_succeeds_with_warnings(tmp_path):
    workdir = make_m083r_workdir(tmp_path)
    paths = write_m084_optimizer_closeout_chain(tmp_path, workdir)

    report = build_lambda_diloco_optimizer_closeout_from_paths(
        success_record=paths["success"],
        reconciliation=paths["reconciliation"],
        evidence_package=paths["evidence"],
    )

    assert report.closeout_status == "closed_with_warnings"
    assert report.closeout_succeeded is True
    assert report.diloco_optimizer_success is True
    assert report.optimizer_semantics_confirmed is True
    assert report.no_real_training is True
    assert report.launch_ready is False
    assert report.launch_allowed is False
