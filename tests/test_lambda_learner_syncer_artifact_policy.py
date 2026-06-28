from __future__ import annotations

from lambda_m079s_helpers import write_m079r_manifest

from decodilo.lambda_cloud.learner_syncer_artifact_policy import (
    build_lambda_learner_syncer_artifact_policy_from_path,
)
from decodilo.lambda_cloud.remote_vslice_declared_artifact_policy import (
    build_lambda_remote_vslice_declared_artifact_policy_from_path,
    write_lambda_remote_vslice_declared_artifact_policy,
)


def test_learner_syncer_artifact_policy_accepts_manifest_declared_path(tmp_path):
    manifest = write_m079r_manifest(tmp_path / "manifest.json")
    declared_path = tmp_path / "declared-policy.json"
    write_lambda_remote_vslice_declared_artifact_policy(
        declared_path,
        build_lambda_remote_vslice_declared_artifact_policy_from_path(
            manifest=manifest,
        ),
    )

    policy = build_lambda_learner_syncer_artifact_policy_from_path(
        declared_artifact_policy=declared_path,
    )

    assert policy.policy_status == "policy_defined"
    assert policy.content_capture_allowed is True
    assert policy.capture_on_success is True
    assert policy.capture_on_failure is True
    assert policy.no_arbitrary_file_reads is True
