from __future__ import annotations

from lambda_m082_helpers import make_m081r2_workdir, write_m082_closeout_chain

from decodilo.lambda_cloud.diloco_synthetic_evidence_package import (
    build_lambda_diloco_synthetic_evidence_package_from_paths,
)


def test_diloco_synthetic_evidence_package_complete(tmp_path):
    workdir = make_m081r2_workdir(tmp_path)
    paths = write_m082_closeout_chain(tmp_path, workdir)

    package = build_lambda_diloco_synthetic_evidence_package_from_paths(
        success_record=paths["success"],
        reconciliation=paths["reconciliation"],
    )

    assert package.evidence_complete is True
    assert package.diloco_synthetic_success is True
    assert package.optimizer_claim_honesty_confirmed is True
    assert package.launch_ready is False
    assert package.launch_allowed is False
