from __future__ import annotations

from lambda_m080_helpers import make_m079r2_workdir, write_m080_closeout_chain

from decodilo.lambda_cloud.diloco_synthetic_readiness import (
    build_lambda_diloco_synthetic_readiness_from_path,
)


def test_diloco_synthetic_readiness_ready_after_learner_syncer_closeout(tmp_path):
    workdir = make_m079r2_workdir(tmp_path)
    paths = write_m080_closeout_chain(tmp_path, workdir)

    readiness = build_lambda_diloco_synthetic_readiness_from_path(
        learner_syncer_closeout=paths["closeout"],
    )

    assert readiness.readiness_status == "ready_for_future_diloco_synthetic_planning"
    assert readiness.learner_syncer_smoke_ready is True
    assert readiness.one_sync_update_round_default is True
    assert readiness.no_real_training is True
    assert readiness.launch_ready is False
    assert readiness.launch_allowed is False
