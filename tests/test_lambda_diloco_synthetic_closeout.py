from __future__ import annotations

from lambda_m082_helpers import make_m081r2_workdir, write_m082_closeout_chain

from decodilo.lambda_cloud.diloco_synthetic_closeout import (
    build_lambda_diloco_synthetic_closeout_from_paths,
)


def test_diloco_synthetic_closeout_succeeds_with_warnings(tmp_path):
    workdir = make_m081r2_workdir(tmp_path)
    paths = write_m082_closeout_chain(tmp_path, workdir)

    closeout = build_lambda_diloco_synthetic_closeout_from_paths(
        success_record=paths["success"],
        reconciliation=paths["reconciliation"],
        evidence_package=paths["evidence"],
    )

    assert closeout.closeout_succeeded is True
    assert closeout.closeout_status in {"closed_success", "closed_with_warnings"}
    assert closeout.optimization_fidelity == "diloco_shaped_protocol_only"
    assert closeout.optimizer_claim_honesty_confirmed is True
    assert closeout.launch_ready is False
    assert closeout.launch_allowed is False
