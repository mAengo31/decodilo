from __future__ import annotations

from lambda_m075s_helpers import make_m075r_manifest

from decodilo.lambda_cloud.remote_vslice_expected_artifact_policy import (
    build_lambda_remote_vslice_expected_artifact_policy_from_path,
    write_lambda_remote_vslice_expected_artifact_policy,
)
from decodilo.lambda_cloud.runtime_smoke_artifact_body_policy import (
    build_lambda_runtime_smoke_artifact_body_policy_from_path,
)
from decodilo.lambda_cloud.runtime_smoke_artifact_parser import (
    RUNTIME_SMOKE_DECLARED_ARTIFACT_PATH,
)


def test_artifact_body_policy_scopes_raw_content_to_declared_json(tmp_path):
    manifest = make_m075r_manifest(tmp_path / "manifest.json")
    expected_path = tmp_path / "expected.json"
    write_lambda_remote_vslice_expected_artifact_policy(
        expected_path,
        build_lambda_remote_vslice_expected_artifact_policy_from_path(
            manifest=manifest,
        ),
    )

    policy = build_lambda_runtime_smoke_artifact_body_policy_from_path(
        expected_artifact_policy=expected_path,
    )

    assert policy.policy_status == "policy_defined"
    assert policy.declared_artifact_path == RUNTIME_SMOKE_DECLARED_ARTIFACT_PATH
    assert policy.content_capture_allowed is True
    assert policy.max_content_bytes <= 32768
    assert policy.capture_on_success is True
    assert policy.capture_on_failure is True
    assert policy.secret_scan_required is True
    assert policy.no_arbitrary_file_reads is True
    assert policy.no_directory_reads is True
    assert policy.launch_ready is False
    assert policy.launch_allowed is False
