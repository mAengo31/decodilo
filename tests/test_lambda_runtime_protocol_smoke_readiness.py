from lambda_m074_helpers import make_m073r2_workdir, write_m074_closeout_chain

from decodilo.lambda_cloud.runtime_protocol_smoke_readiness import (
    build_lambda_runtime_protocol_smoke_readiness_from_path,
)


def test_runtime_protocol_smoke_readiness_after_tiny_smoke_closeout(tmp_path):
    workdir = make_m073r2_workdir(tmp_path)
    paths = write_m074_closeout_chain(tmp_path, workdir)

    readiness = build_lambda_runtime_protocol_smoke_readiness_from_path(
        tiny_smoke_closeout=paths["closeout"],
    )

    assert readiness.readiness_status == "ready_for_future_runtime_protocol_smoke_planning"
    assert readiness.cloud_lifecycle_ready is True
    assert readiness.tiny_smoke_ready is True
    assert readiness.launch_ready is False
    assert readiness.launch_allowed is False
