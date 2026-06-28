from __future__ import annotations

from lambda_m084_helpers import make_m083r_workdir, write_m084_optimizer_closeout_chain

from decodilo.lambda_cloud.diloco_optimizer_evidence_package import (
    build_lambda_diloco_optimizer_evidence_package_from_paths,
)


def test_diloco_optimizer_evidence_package_is_complete(tmp_path):
    workdir = make_m083r_workdir(tmp_path)
    paths = write_m084_optimizer_closeout_chain(tmp_path, workdir)

    report = build_lambda_diloco_optimizer_evidence_package_from_paths(
        success_record=paths["success"],
        reconciliation=paths["reconciliation"],
    )

    assert report.evidence_complete is True
    assert report.diloco_optimizer_success is True
    assert report.reconciliation_passed is True
    assert report.optimizer_semantics_confirmed is True
    assert report.missing_items == []
    assert report.hash_mismatches == []
    assert report.launch_ready is False
    assert report.launch_allowed is False
