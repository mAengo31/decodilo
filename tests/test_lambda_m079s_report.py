from __future__ import annotations

import json

from lambda_m079s_helpers import (
    learner_syncer_success_artifact,
    make_m079r_artifact_capture_blocked_workdir,
    write_m079r_manifest,
)

from decodilo.lambda_cloud.learner_syncer_artifact_parser import (
    parse_learner_syncer_artifact_file,
    write_learner_syncer_artifact_parser_report,
)
from decodilo.lambda_cloud.learner_syncer_smoke_attempt_closeout import (
    build_lambda_learner_syncer_smoke_attempt_closeout_from_paths,
    write_lambda_learner_syncer_smoke_attempt_closeout,
)
from decodilo.lambda_cloud.m079r2_next_synthetic_experiment_authorization import (
    build_lambda_m079r2_next_synthetic_experiment_authorization_from_paths,
    write_lambda_m079r2_next_synthetic_experiment_authorization,
)
from decodilo.lambda_cloud.m079r2_next_synthetic_experiment_runbook_preview import (
    build_lambda_m079r2_next_synthetic_experiment_runbook_preview_from_paths,
    write_lambda_m079r2_next_synthetic_experiment_runbook_preview,
)
from decodilo.lambda_cloud.m079r_next_synthetic_experiment_authorization import (
    LambdaM079RNextSyntheticExperimentAuthorization,
    write_lambda_m079r_next_synthetic_experiment_authorization,
)
from decodilo.lambda_cloud.m079s_report import build_lambda_m079s_report_from_paths
from decodilo.lambda_cloud.remote_vslice_declared_artifact_policy import (
    build_lambda_remote_vslice_declared_artifact_policy_from_path,
    write_lambda_remote_vslice_declared_artifact_policy,
)


def test_m079s_report_passes_when_retry_artifacts_are_ready(tmp_path):
    workdir = make_m079r_artifact_capture_blocked_workdir(tmp_path)
    closeout_path = tmp_path / "closeout.json"
    policy_path = tmp_path / "policy.json"
    parser_path = tmp_path / "parser.json"
    previous_path = tmp_path / "previous.json"
    authorization_path = tmp_path / "authorization.json"
    runbook_path = tmp_path / "runbook.json"
    fixture = tmp_path / "fixture.json"
    fixture.write_text(json.dumps(learner_syncer_success_artifact()), encoding="utf-8")
    write_lambda_learner_syncer_smoke_attempt_closeout(
        closeout_path,
        build_lambda_learner_syncer_smoke_attempt_closeout_from_paths(
            workdir=workdir,
        ),
    )
    write_lambda_remote_vslice_declared_artifact_policy(
        policy_path,
        build_lambda_remote_vslice_declared_artifact_policy_from_path(
            manifest=write_m079r_manifest(tmp_path / "manifest.json"),
        ),
    )
    write_learner_syncer_artifact_parser_report(
        parser_path,
        parse_learner_syncer_artifact_file(
            artifact_path=fixture,
            policy=policy_path,
        ),
    )
    write_lambda_m079r_next_synthetic_experiment_authorization(
        previous_path,
        LambdaM079RNextSyntheticExperimentAuthorization(
            authorization_status="authorized_for_future_m079r_next_synthetic_experiment",
            command_category="dev_learner_syncer_smoke_one_step",
        ),
    )
    write_lambda_m079r2_next_synthetic_experiment_authorization(
        authorization_path,
        build_lambda_m079r2_next_synthetic_experiment_authorization_from_paths(
            attempt_closeout=closeout_path,
            declared_artifact_policy=policy_path,
            previous_authorization=previous_path,
        ),
    )
    write_lambda_m079r2_next_synthetic_experiment_runbook_preview(
        runbook_path,
        build_lambda_m079r2_next_synthetic_experiment_runbook_preview_from_paths(
            authorization=authorization_path,
            declared_artifact_policy=policy_path,
        ),
    )

    report = build_lambda_m079s_report_from_paths(
        attempt_closeout=closeout_path,
        declared_artifact_policy=policy_path,
        parser_fixture_report=parser_path,
        authorization=authorization_path,
        runbook_preview=runbook_path,
    )

    assert report.report_passed is True
    assert report.command_passed is True
    assert report.artifact_capture_blocked is True
    assert report.declared_artifact_policy_fixed is True
    assert (
        report.m079r2_authorization_status
        == "authorized_for_future_m079r2_next_synthetic_experiment_retry"
    )
    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.billable_action_performed is False
