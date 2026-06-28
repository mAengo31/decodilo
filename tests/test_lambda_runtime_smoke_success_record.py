from __future__ import annotations

from lambda_m076_helpers import make_m075r4_workdir

from decodilo.lambda_cloud.runtime_smoke_success_record import (
    build_lambda_runtime_smoke_success_record_from_paths,
)


def test_runtime_smoke_success_record_classifies_m075r4_success(tmp_path):
    workdir = make_m075r4_workdir(tmp_path)

    record = build_lambda_runtime_smoke_success_record_from_paths(workdir=workdir)

    assert record.success_status == "runtime_protocol_smoke_success"
    assert record.infrastructure_passed is True
    assert record.runtime_smoke_command_passed is True
    assert record.runtime_smoke_status == "passed"
    assert record.protocol_or_event_check_passed is True
    assert record.replay_or_metric_check_passed is True
    assert record.artifact_body_persisted is True
    assert record.parsed_summary_persisted is True
    assert record.final_instance_count == 0
    assert record.final_unmanaged_count == 0
    assert record.launch_ready is False
    assert record.launch_allowed is False
