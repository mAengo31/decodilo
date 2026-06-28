from __future__ import annotations

from lambda_m079s_helpers import make_m079r_artifact_capture_blocked_workdir

from decodilo.lambda_cloud.learner_syncer_smoke_attempt_closeout import (
    LEARNER_SYNCER_DECLARED_ARTIFACT_PATH,
    build_lambda_learner_syncer_smoke_attempt_closeout_from_paths,
)


def test_learner_syncer_smoke_attempt_closeout_classifies_capture_block(tmp_path):
    workdir = make_m079r_artifact_capture_blocked_workdir(tmp_path)

    closeout = build_lambda_learner_syncer_smoke_attempt_closeout_from_paths(
        workdir=workdir,
    )

    assert (
        closeout.closeout_status
        == "closed_learner_syncer_smoke_command_passed_artifact_capture_blocked"
    )
    assert closeout.closeout_succeeded is True
    assert closeout.infrastructure_passed is True
    assert closeout.learner_syncer_smoke_exit_code == 0
    assert closeout.learner_syncer_smoke_command_passed is True
    assert closeout.expected_artifact_path == LEARNER_SYNCER_DECLARED_ARTIFACT_PATH
    assert closeout.artifact_capture_attempted is True
    assert closeout.artifact_capture_status == "blocked_undeclared_artifact_path"
    assert closeout.artifact_metadata_persisted is False
    assert closeout.artifact_body_persisted is False
    assert closeout.artifact_parsed_summary_persisted is False
    assert closeout.failure_diagnosis_status == "declared_artifact_policy_path_missing"
    assert closeout.termination_verified is True
    assert closeout.final_instance_count == 0
    assert closeout.final_unmanaged_count == 0
    assert closeout.launch_ready is False
    assert closeout.launch_allowed is False
