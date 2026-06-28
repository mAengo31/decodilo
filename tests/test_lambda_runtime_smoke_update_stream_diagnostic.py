from __future__ import annotations

from pathlib import Path

from lambda_m075u_helpers import (
    make_m075r3_update_stream_failure_workdir,
    make_runtime_smoke_report,
)

from decodilo.lambda_cloud.runtime_smoke_update_stream_diagnostic import (
    build_lambda_runtime_smoke_update_stream_diagnostic_from_paths,
)
from decodilo.lambda_cloud.runtime_smoke_update_stream_failure_record import (
    build_lambda_runtime_smoke_update_stream_failure_record_from_paths,
    write_lambda_runtime_smoke_update_stream_failure_record,
)


def test_update_stream_diagnostic_identifies_local_pass_remote_fail(tmp_path):
    workdir = make_m075r3_update_stream_failure_workdir(tmp_path)
    record_path = tmp_path / "record.json"
    write_lambda_runtime_smoke_update_stream_failure_record(
        record_path,
        build_lambda_runtime_smoke_update_stream_failure_record_from_paths(
            workdir=workdir
        ),
    )
    make_runtime_smoke_report(Path("/tmp/decodilo-runtime-smoke-m075u-before.json"))
    make_runtime_smoke_report(Path("/tmp/decodilo-runtime-smoke-m075u-after.json"))

    diagnostic = build_lambda_runtime_smoke_update_stream_diagnostic_from_paths(
        failure_record=record_path,
        source_root=Path.cwd(),
    )

    assert diagnostic.diagnostic_status == "diagnosed_update_stream_timeout_path"
    assert diagnostic.local_function_or_check == (
        "decodilo.dev.runtime_smoke._run_update_stream_check"
    )
    assert diagnostic.update_stream_event_source == (
        "decodilo.runtime.update_stream.UpdateStream._update_event"
    )
    assert diagnostic.producer_started is True
    assert diagnostic.consumer_waits_on_correct_stream is True
    assert diagnostic.timeout_configurable is True
    assert diagnostic.local_reproduction_status == "local_pass_remote_fail"
    assert diagnostic.local_fix_verified is True
    assert diagnostic.launch_ready is False
    assert diagnostic.launch_allowed is False
