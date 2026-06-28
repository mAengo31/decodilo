from __future__ import annotations

import pytest
from lambda_m079s_helpers import write_m079r_manifest

from decodilo.lambda_cloud.learner_syncer_smoke_attempt_closeout import (
    LEARNER_SYNCER_DECLARED_ARTIFACT_PATH,
)
from decodilo.lambda_cloud.remote_vslice_declared_artifact_policy import (
    build_lambda_remote_vslice_declared_artifact_policy_from_path,
)


def test_declared_artifact_policy_uses_manifest_declared_learner_syncer_path(tmp_path):
    manifest = write_m079r_manifest(tmp_path / "manifest.json")

    policy = build_lambda_remote_vslice_declared_artifact_policy_from_path(
        manifest=manifest,
    )

    assert policy.policy_status == "policy_defined"
    assert policy.declared_artifact_path == LEARNER_SYNCER_DECLARED_ARTIFACT_PATH
    assert policy.declared_artifact_paths == [LEARNER_SYNCER_DECLARED_ARTIFACT_PATH]
    assert policy.capture_on_success is True
    assert policy.capture_on_failure is True
    assert policy.no_arbitrary_file_reads is True
    assert policy.launch_ready is False
    assert policy.launch_allowed is False


@pytest.mark.parametrize(
    "unsafe_path",
    [
        "relative.json",
        "/tmp/../secret.json",
        "/tmp/*.json",
        "/var/tmp/decodilo-learner-syncer-smoke.json",
    ],
)
def test_declared_artifact_policy_rejects_unsafe_manifest_paths(tmp_path, unsafe_path):
    manifest = write_m079r_manifest(tmp_path / "manifest.json", out_path=unsafe_path)

    policy = build_lambda_remote_vslice_declared_artifact_policy_from_path(
        manifest=manifest,
    )

    assert policy.policy_status == "blocked"
    assert "declared_artifact_path_not_safe" in policy.blockers
