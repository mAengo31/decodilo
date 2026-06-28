from __future__ import annotations

from pathlib import Path

from lambda_m075u_helpers import (
    make_m075r3_update_stream_failure_workdir,
    make_runtime_smoke_report,
)

from decodilo.lambda_cloud.m075r4_runtime_smoke_retry_authorization import (
    build_lambda_m075r4_runtime_smoke_retry_authorization_from_paths,
    write_lambda_m075r4_runtime_smoke_retry_authorization,
)
from decodilo.lambda_cloud.m075r4_runtime_smoke_runbook_preview import (
    build_lambda_m075r4_runtime_smoke_runbook_preview_from_path,
    write_lambda_m075r4_runtime_smoke_runbook_preview,
)
from decodilo.lambda_cloud.m075u_report import build_lambda_m075u_report_from_paths
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


def test_m075u_report_passes_after_local_update_stream_fix(tmp_path):
    workdir = make_m075r3_update_stream_failure_workdir(tmp_path)
    failure_record_path = tmp_path / "failure-record.json"
    write_lambda_runtime_smoke_update_stream_failure_record(
        failure_record_path,
        build_lambda_runtime_smoke_update_stream_failure_record_from_paths(
            workdir=workdir
        ),
    )
    closeout_path = tmp_path / "closeout.json"
    write_lambda_runtime_smoke_update_stream_closeout(
        closeout_path,
        build_lambda_runtime_smoke_update_stream_closeout_from_path(
            failure_record=failure_record_path
        ),
    )
    before_path = tmp_path / "before.json"
    after_path = tmp_path / "after.json"
    make_runtime_smoke_report(before_path)
    make_runtime_smoke_report(after_path)
    make_runtime_smoke_report(Path("/tmp/decodilo-runtime-smoke-m075u-before.json"))
    make_runtime_smoke_report(Path("/tmp/decodilo-runtime-smoke-m075u-after.json"))
    diagnostic_path = tmp_path / "diagnostic.json"
    write_lambda_runtime_smoke_update_stream_diagnostic(
        diagnostic_path,
        build_lambda_runtime_smoke_update_stream_diagnostic_from_paths(
            failure_record=failure_record_path,
            source_root=Path.cwd(),
        ),
    )
    authorization_path = tmp_path / "authorization.json"
    write_lambda_m075r4_runtime_smoke_retry_authorization(
        authorization_path,
        build_lambda_m075r4_runtime_smoke_retry_authorization_from_paths(
            update_stream_closeout=closeout_path,
            diagnostic=diagnostic_path,
            local_after_report=after_path,
        ),
    )
    runbook_path = tmp_path / "runbook.json"
    write_lambda_m075r4_runtime_smoke_runbook_preview(
        runbook_path,
        build_lambda_m075r4_runtime_smoke_runbook_preview_from_path(
            authorization=authorization_path,
        ),
    )

    report = build_lambda_m075u_report_from_paths(
        failure_record=failure_record_path,
        closeout=closeout_path,
        diagnostic=diagnostic_path,
        local_before_report=before_path,
        local_after_report=after_path,
        authorization=authorization_path,
        runbook_preview=runbook_path,
    )

    assert report.report_passed is True
    assert report.m075r3_failure_status == "runtime_smoke_update_stream_failed"
    assert report.m075r3_error_classification == "update_stream_check_failed"
    assert report.local_reproduction_status == "local_pass_remote_fail"
    assert report.runtime_smoke_now_passes_locally is True
    assert report.m075r4_authorization_status == (
        "authorized_for_future_m075r4_runtime_smoke_retry"
    )
    assert report.launch_ready is False
    assert report.launch_allowed is False
