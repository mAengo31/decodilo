from __future__ import annotations

from lambda_m082_helpers import make_m081r2_workdir, write_m082_closeout_chain
from lambda_m084_helpers import (
    make_m083r_workdir,
    write_learner_syncer_closeout,
    write_m084_optimizer_closeout_chain,
)

from decodilo.lambda_cloud.integrated_diloco_synthetic_readiness import (
    build_lambda_integrated_diloco_synthetic_readiness_from_paths,
)


def test_integrated_diloco_readiness_passes_after_three_baselines(tmp_path):
    diloco_workdir = make_m081r2_workdir(tmp_path)
    diloco_paths = write_m082_closeout_chain(tmp_path, diloco_workdir)
    optimizer_workdir = make_m083r_workdir(tmp_path)
    optimizer_paths = write_m084_optimizer_closeout_chain(tmp_path, optimizer_workdir)
    learner_closeout = write_learner_syncer_closeout(tmp_path)

    report = build_lambda_integrated_diloco_synthetic_readiness_from_paths(
        diloco_synthetic_closeout=diloco_paths["closeout"],
        optimizer_closeout=optimizer_paths["closeout"],
        learner_syncer_closeout=learner_closeout,
    )

    assert report.readiness_status == "ready_for_future_integrated_diloco_planning"
    assert report.remote_learner_syncer_smoke_ready is True
    assert report.remote_diloco_shaped_protocol_smoke_ready is True
    assert report.remote_optimizer_fidelity_smoke_ready is True
    assert report.no_real_training is True
    assert report.launch_ready is False
    assert report.launch_allowed is False
