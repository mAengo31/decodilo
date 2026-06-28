from __future__ import annotations

from lambda_m078_helpers import make_m077r_workdir, write_m078_closeout_chain

from decodilo.lambda_cloud.next_synthetic_experiment_readiness import (
    build_lambda_next_synthetic_experiment_readiness_from_path,
)


def test_next_synthetic_experiment_readiness_after_m077r_closeout(tmp_path):
    workdir = make_m077r_workdir(tmp_path)
    paths = write_m078_closeout_chain(tmp_path, workdir)

    readiness = build_lambda_next_synthetic_experiment_readiness_from_path(
        synthetic_experiment_closeout=paths["closeout"],
    )

    assert (
        readiness.readiness_status
        == "ready_for_future_next_synthetic_experiment_planning"
    )
    assert readiness.cloud_lifecycle_ready is True
    assert readiness.first_remote_synthetic_experiment_ready is True
    assert readiness.no_real_training is True
    assert readiness.launch_ready is False
    assert readiness.launch_allowed is False
