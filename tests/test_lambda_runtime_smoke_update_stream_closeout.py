from __future__ import annotations

from lambda_m075u_helpers import make_m075r3_update_stream_failure_workdir

from decodilo.lambda_cloud.runtime_smoke_update_stream_closeout import (
    build_lambda_runtime_smoke_update_stream_closeout_from_path,
)
from decodilo.lambda_cloud.runtime_smoke_update_stream_failure_record import (
    build_lambda_runtime_smoke_update_stream_failure_record_from_paths,
    write_lambda_runtime_smoke_update_stream_failure_record,
)


def test_update_stream_closeout_requires_local_fix_before_retry(tmp_path):
    workdir = make_m075r3_update_stream_failure_workdir(tmp_path)
    record_path = tmp_path / "record.json"
    write_lambda_runtime_smoke_update_stream_failure_record(
        record_path,
        build_lambda_runtime_smoke_update_stream_failure_record_from_paths(
            workdir=workdir
        ),
    )

    closeout = build_lambda_runtime_smoke_update_stream_closeout_from_path(
        failure_record=record_path
    )

    assert closeout.closeout_status == "closed_runtime_smoke_update_stream_timeout"
    assert closeout.closeout_succeeded is True
    assert closeout.retry_requires_local_update_stream_fix is True
    assert closeout.infrastructure_passed is True
    assert closeout.update_stream_failure_classified is True
    assert closeout.artifact_body_or_summary_available is True
    assert closeout.launch_ready is False
    assert closeout.launch_allowed is False
