from __future__ import annotations

from lambda_m075s_helpers import make_m075r2_runtime_smoke_metadata_workdir

from decodilo.lambda_cloud.runtime_smoke_attempt_closeout import (
    build_lambda_runtime_smoke_attempt_closeout_from_paths,
)


def test_runtime_smoke_attempt_closeout_records_metadata_gap(tmp_path):
    workdir = make_m075r2_runtime_smoke_metadata_workdir(tmp_path)

    closeout = build_lambda_runtime_smoke_attempt_closeout_from_paths(workdir=workdir)

    assert closeout.closeout_status == (
        "closed_runtime_smoke_command_failed_with_artifact_metadata_captured"
    )
    assert closeout.infrastructure_passed is True
    assert closeout.runtime_smoke_exit_code == 1
    assert closeout.artifact_exists is True
    assert closeout.artifact_size == 1367
    assert closeout.artifact_secret_scan_passed is True
    assert closeout.artifact_body_persisted is False
    assert closeout.artifact_parsed_summary_persisted is False
    assert closeout.failure_diagnosis_status == "artifact_body_or_summary_needed"
    assert closeout.termination_verified is True
    assert closeout.final_instance_count == 0
    assert closeout.final_unmanaged_count == 0
    assert closeout.launch_ready is False
    assert closeout.launch_allowed is False
