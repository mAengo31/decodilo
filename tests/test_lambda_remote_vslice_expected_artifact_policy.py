from __future__ import annotations

from lambda_m075s_helpers import make_m075r_manifest

from decodilo.lambda_cloud.remote_vslice_expected_artifact_policy import (
    build_lambda_remote_vslice_expected_artifact_policy_from_path,
)


def test_expected_artifact_policy_accepts_declared_m075r_runtime_smoke_artifact(
    tmp_path,
):
    manifest = make_m075r_manifest(tmp_path / "manifest.json")

    policy = build_lambda_remote_vslice_expected_artifact_policy_from_path(
        manifest=manifest,
    )

    assert policy.policy_status == "policy_defined"
    assert policy.expected_output_artifact_path == "/tmp/decodilo-runtime-smoke.json"
    assert policy.max_artifact_bytes == 32768
    assert policy.capture_allowed_on_failure is True
    assert policy.no_arbitrary_file_reads is True
    assert policy.no_directory_traversal is True
    assert policy.launch_ready is False
    assert policy.launch_allowed is False
