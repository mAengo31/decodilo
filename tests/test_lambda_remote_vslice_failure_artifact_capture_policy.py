from __future__ import annotations

from lambda_m075s_helpers import make_m075r_manifest

from decodilo.lambda_cloud.remote_vslice_expected_artifact_policy import (
    build_lambda_remote_vslice_expected_artifact_policy_from_path,
    write_lambda_remote_vslice_expected_artifact_policy,
)
from decodilo.lambda_cloud.remote_vslice_failure_artifact_capture_policy import (
    build_lambda_remote_vslice_failure_artifact_capture_policy_from_paths,
)
from decodilo.lambda_cloud.runtime_smoke_failure_evidence_policy import (
    build_lambda_runtime_smoke_failure_evidence_policy,
    write_lambda_runtime_smoke_failure_evidence_policy,
)


def test_failure_artifact_capture_policy_passes_for_predeclared_artifact(tmp_path):
    manifest = make_m075r_manifest(tmp_path / "manifest.json")
    artifact_policy = tmp_path / "artifact-policy.json"
    failure_policy = tmp_path / "failure-policy.json"
    write_lambda_remote_vslice_expected_artifact_policy(
        artifact_policy,
        build_lambda_remote_vslice_expected_artifact_policy_from_path(
            manifest=manifest,
        ),
    )
    write_lambda_runtime_smoke_failure_evidence_policy(
        failure_policy,
        build_lambda_runtime_smoke_failure_evidence_policy(),
    )

    policy = build_lambda_remote_vslice_failure_artifact_capture_policy_from_paths(
        expected_artifact_policy=artifact_policy,
        failure_evidence_policy=failure_policy,
    )

    assert policy.policy_passed is True
    assert policy.capture_on_failure_allowed is True
    assert policy.capture_scope == "predeclared_artifact_only"
    assert policy.no_arbitrary_file_read is True
    assert policy.no_unbounded_transfer is True
    assert policy.launch_ready is False
    assert policy.launch_allowed is False
