from __future__ import annotations

from lambda_m081s_helpers import make_m081r_artifact_capture_blocked_workdir

from decodilo.lambda_cloud.diloco_artifact_parser import (
    DILOCO_SMOKE_DECLARED_ARTIFACT_PATH,
)
from decodilo.lambda_cloud.diloco_smoke_attempt_closeout import (
    build_lambda_diloco_smoke_attempt_closeout_from_paths,
)


def test_diloco_attempt_closeout_classifies_command_pass_capture_blocked(tmp_path):
    workdir = make_m081r_artifact_capture_blocked_workdir(tmp_path)

    closeout = build_lambda_diloco_smoke_attempt_closeout_from_paths(workdir=workdir)

    assert (
        closeout.closeout_status
        == "closed_diloco_smoke_command_passed_artifact_capture_blocked"
    )
    assert closeout.closeout_succeeded is True
    assert closeout.diloco_smoke_command_passed is True
    assert closeout.expected_artifact_path == DILOCO_SMOKE_DECLARED_ARTIFACT_PATH
    assert closeout.artifact_capture_status == "blocked_undeclared_artifact_path"
    assert closeout.artifact_metadata_persisted is False
    assert closeout.artifact_body_persisted is False
    assert closeout.artifact_parsed_summary_persisted is False
    assert closeout.termination_verified is True
    assert closeout.final_instance_count == 0
    assert closeout.final_unmanaged_count == 0
    assert closeout.launch_ready is False
    assert closeout.launch_allowed is False
    assert closeout.billable_action_performed is False
