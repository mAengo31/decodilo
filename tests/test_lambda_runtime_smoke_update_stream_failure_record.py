from __future__ import annotations

from lambda_m075u_helpers import make_m075r3_update_stream_failure_workdir

from decodilo.lambda_cloud.runtime_smoke_update_stream_failure_record import (
    build_lambda_runtime_smoke_update_stream_failure_record_from_paths,
)


def test_update_stream_failure_record_classifies_m075r3_failure(tmp_path):
    workdir = make_m075r3_update_stream_failure_workdir(tmp_path)

    record = build_lambda_runtime_smoke_update_stream_failure_record_from_paths(
        workdir=workdir
    )

    assert record.failure_status == "runtime_smoke_update_stream_failed"
    assert record.failed_stage == "runtime_smoke_command"
    assert record.failed_check == "protocol_or_event_check"
    assert record.error_classification == "update_stream_check_failed"
    assert record.safe_error == "update_stream_check_failed:TimeoutError"
    assert record.artifact_body_persisted is True
    assert record.parsed_summary_persisted is True
    assert record.infrastructure_passed is True
    assert record.no_internet_install is True
    assert record.no_downloads is True
    assert record.no_training is True
    assert record.termination_verified is True
    assert record.final_instance_count == 0
    assert record.final_unmanaged_count == 0
    assert record.launch_ready is False
    assert record.launch_allowed is False
