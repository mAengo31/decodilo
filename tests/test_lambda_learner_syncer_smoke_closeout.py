from __future__ import annotations

from lambda_m080_helpers import make_m079r2_workdir, write_m080_closeout_chain

from decodilo.lambda_cloud.learner_syncer_smoke_closeout import (
    build_lambda_learner_syncer_smoke_closeout_from_paths,
)


def test_learner_syncer_closeout_succeeds_with_warnings(tmp_path):
    workdir = make_m079r2_workdir(tmp_path)
    paths = write_m080_closeout_chain(tmp_path, workdir)

    closeout = build_lambda_learner_syncer_smoke_closeout_from_paths(
        success_record=paths["success"],
        reconciliation=paths["reconciliation"],
        evidence_package=paths["evidence"],
    )

    assert closeout.closeout_succeeded is True
    assert closeout.closeout_status in {"closed_success", "closed_with_warnings"}
    assert closeout.learner_syncer_smoke_success is True
    assert closeout.termination_verified is True
    assert closeout.launch_ready is False
    assert closeout.launch_allowed is False
