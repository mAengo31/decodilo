from __future__ import annotations

from lambda_m075s_helpers import make_m075r_runtime_smoke_failure_workdir

from decodilo.lambda_cloud.runtime_smoke_failure_closeout import (
    build_lambda_runtime_smoke_failure_closeout_from_path,
)
from decodilo.lambda_cloud.runtime_smoke_failure_record import (
    build_lambda_runtime_smoke_failure_record_from_paths,
    write_lambda_runtime_smoke_failure_record,
)


def test_runtime_smoke_failure_closeout_requires_failure_artifact_capture(tmp_path):
    workdir = make_m075r_runtime_smoke_failure_workdir(tmp_path)
    record_path = tmp_path / "failure-record.json"
    write_lambda_runtime_smoke_failure_record(
        record_path,
        build_lambda_runtime_smoke_failure_record_from_paths(workdir=workdir),
    )

    closeout = build_lambda_runtime_smoke_failure_closeout_from_path(
        failure_record=record_path,
    )

    assert closeout.closeout_status == (
        "closed_runtime_smoke_command_failed_evidence_insufficient"
    )
    assert closeout.closeout_succeeded is True
    assert closeout.infrastructure_clean is True
    assert closeout.decodilo_runtime_smoke_failed is True
    assert closeout.failure_evidence_insufficient is True
    assert closeout.retry_requires_failure_artifact_capture is True
    assert closeout.launch_ready is False
    assert closeout.launch_allowed is False
