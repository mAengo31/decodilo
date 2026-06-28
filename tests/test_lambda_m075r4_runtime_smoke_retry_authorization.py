from __future__ import annotations

from pathlib import Path

from lambda_m075u_helpers import (
    make_m075r3_update_stream_failure_workdir,
    make_runtime_smoke_report,
)

from decodilo.lambda_cloud.m075r4_runtime_smoke_retry_authorization import (
    build_lambda_m075r4_runtime_smoke_retry_authorization_from_paths,
)
from decodilo.lambda_cloud.runtime_smoke_update_stream_closeout import (
    build_lambda_runtime_smoke_update_stream_closeout_from_path,
    write_lambda_runtime_smoke_update_stream_closeout,
)
from decodilo.lambda_cloud.runtime_smoke_update_stream_diagnostic import (
    build_lambda_runtime_smoke_update_stream_diagnostic_from_paths,
    write_lambda_runtime_smoke_update_stream_diagnostic,
)
from decodilo.lambda_cloud.runtime_smoke_update_stream_failure_record import (
    build_lambda_runtime_smoke_update_stream_failure_record_from_paths,
    write_lambda_runtime_smoke_update_stream_failure_record,
)


def test_m075r4_authorization_requires_passing_local_after_report(tmp_path):
    workdir = make_m075r3_update_stream_failure_workdir(tmp_path)
    record_path = tmp_path / "record.json"
    write_lambda_runtime_smoke_update_stream_failure_record(
        record_path,
        build_lambda_runtime_smoke_update_stream_failure_record_from_paths(
            workdir=workdir
        ),
    )
    closeout_path = tmp_path / "closeout.json"
    write_lambda_runtime_smoke_update_stream_closeout(
        closeout_path,
        build_lambda_runtime_smoke_update_stream_closeout_from_path(
            failure_record=record_path
        ),
    )
    make_runtime_smoke_report(Path("/tmp/decodilo-runtime-smoke-m075u-before.json"))
    local_after = tmp_path / "after.json"
    make_runtime_smoke_report(Path("/tmp/decodilo-runtime-smoke-m075u-after.json"))
    make_runtime_smoke_report(local_after)
    diagnostic_path = tmp_path / "diagnostic.json"
    write_lambda_runtime_smoke_update_stream_diagnostic(
        diagnostic_path,
        build_lambda_runtime_smoke_update_stream_diagnostic_from_paths(
            failure_record=record_path,
            source_root=Path.cwd(),
        ),
    )

    authorization = build_lambda_m075r4_runtime_smoke_retry_authorization_from_paths(
        update_stream_closeout=closeout_path,
        diagnostic=diagnostic_path,
        local_after_report=local_after,
    )

    assert authorization.authorization_status == (
        "authorized_for_future_m075r4_runtime_smoke_retry"
    )
    assert authorization.reason == "local_update_stream_fix_verified"
    assert authorization.run_now is False
    assert authorization.launch_ready is False
    assert authorization.launch_allowed is False
