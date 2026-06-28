from __future__ import annotations

from lambda_m076_helpers import make_m075r4_workdir, write_m076_closeout_chain

from decodilo.lambda_cloud.first_synthetic_experiment_readiness import (
    build_lambda_first_synthetic_experiment_readiness_from_path,
)


def test_first_synthetic_experiment_readiness_is_ready_after_runtime_smoke(tmp_path):
    workdir = make_m075r4_workdir(tmp_path)
    paths = write_m076_closeout_chain(tmp_path, workdir)

    readiness = build_lambda_first_synthetic_experiment_readiness_from_path(
        runtime_smoke_closeout=paths["closeout"],
    )

    assert (
        readiness.readiness_status
        == "ready_for_future_first_synthetic_experiment_planning"
    )
    assert readiness.runtime_protocol_smoke_ready is True
    assert readiness.no_model_or_data_download is True
    assert readiness.launch_ready is False
    assert readiness.launch_allowed is False
