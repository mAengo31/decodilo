from __future__ import annotations

from lambda_m079s_helpers import make_m079r_artifact_capture_blocked_workdir, write_m079r_manifest

from decodilo.lambda_cloud.learner_syncer_smoke_attempt_closeout import (
    build_lambda_learner_syncer_smoke_attempt_closeout_from_paths,
    write_lambda_learner_syncer_smoke_attempt_closeout,
)
from decodilo.lambda_cloud.m079r2_next_synthetic_experiment_authorization import (
    build_lambda_m079r2_next_synthetic_experiment_authorization_from_paths,
)
from decodilo.lambda_cloud.m079r_next_synthetic_experiment_authorization import (
    LambdaM079RNextSyntheticExperimentAuthorization,
    write_lambda_m079r_next_synthetic_experiment_authorization,
)
from decodilo.lambda_cloud.remote_vslice_declared_artifact_policy import (
    build_lambda_remote_vslice_declared_artifact_policy_from_path,
    write_lambda_remote_vslice_declared_artifact_policy,
)


def test_m079r2_authorization_future_only_when_capture_policy_fixed(tmp_path):
    workdir = make_m079r_artifact_capture_blocked_workdir(tmp_path)
    closeout_path = tmp_path / "closeout.json"
    policy_path = tmp_path / "policy.json"
    previous_path = tmp_path / "previous.json"
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
    write_lambda_m079r_next_synthetic_experiment_authorization(
        previous_path,
        LambdaM079RNextSyntheticExperimentAuthorization(
            authorization_status="authorized_for_future_m079r_next_synthetic_experiment",
            command_category="dev_learner_syncer_smoke_one_step",
        ),
    )

    authorization = build_lambda_m079r2_next_synthetic_experiment_authorization_from_paths(
        attempt_closeout=closeout_path,
        declared_artifact_policy=policy_path,
        previous_authorization=previous_path,
    )

    assert (
        authorization.authorization_status
        == "authorized_for_future_m079r2_next_synthetic_experiment_retry"
    )
    assert authorization.reason == "retry_with_manifest_declared_artifact_capture_fixed"
    assert authorization.run_now is False
    assert authorization.launch_ready is False
    assert authorization.launch_allowed is False
