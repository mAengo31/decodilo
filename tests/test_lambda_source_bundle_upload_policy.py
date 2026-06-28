from __future__ import annotations

from decodilo.lambda_cloud.source_bundle_upload_policy import (
    build_lambda_source_dependency_upload_policy_from_path,
)
from decodilo.lambda_cloud.ssh_banner_readiness_policy import (
    build_lambda_ssh_banner_readiness_policy,
    write_lambda_ssh_banner_readiness_policy,
)
from decodilo.lambda_cloud.upload_readiness_policy import (
    build_lambda_upload_readiness_gate_policy_from_path,
    write_lambda_upload_readiness_gate_policy,
)


def test_source_dependency_upload_policy_orders_upload_and_hash_checks(tmp_path) -> None:
    banner = tmp_path / "banner.json"
    gate = tmp_path / "gate.json"
    write_lambda_ssh_banner_readiness_policy(
        banner,
        build_lambda_ssh_banner_readiness_policy(),
    )
    write_lambda_upload_readiness_gate_policy(
        gate,
        build_lambda_upload_readiness_gate_policy_from_path(banner_policy=banner),
    )

    policy = build_lambda_source_dependency_upload_policy_from_path(
        upload_readiness_gate=gate,
    )

    assert policy.upload_policy_status == "policy_defined"
    assert policy.upload_only_after_ssh_banner_readiness is True
    assert policy.verify_source_hash_before_dependency_upload is True
    assert policy.verify_dependency_hash_before_extract_or_install is True
    assert policy.stop_and_terminate_on_source_upload_failure is True
    assert policy.manifest_execution_allowed_before_bundle_verification is False
    assert policy.launch_ready is False
    assert policy.launch_allowed is False
