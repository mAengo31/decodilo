from __future__ import annotations

from lambda_m082_helpers import make_m081r2_workdir, write_m082_closeout_chain

from decodilo.lambda_cloud.diloco_optimizer_readiness import (
    build_lambda_diloco_optimizer_readiness_from_path,
)


def test_diloco_optimizer_readiness_ready_after_diloco_closeout(tmp_path):
    workdir = make_m081r2_workdir(tmp_path)
    paths = write_m082_closeout_chain(tmp_path, workdir)

    readiness = build_lambda_diloco_optimizer_readiness_from_path(
        diloco_synthetic_closeout=paths["closeout"],
    )

    assert readiness.readiness_status == "ready_for_future_diloco_optimizer_planning"
    assert readiness.remote_diloco_shaped_protocol_smoke_ready is True
    assert readiness.desired_inner_adamw_semantics is True
    assert readiness.desired_outer_nesterov_semantics is True
    assert readiness.no_real_model_training is True
    assert readiness.launch_ready is False
    assert readiness.launch_allowed is False
