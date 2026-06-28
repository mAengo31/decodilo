from __future__ import annotations

from decodilo.lambda_cloud.ssh_banner_readiness_policy import (
    build_lambda_ssh_banner_readiness_policy,
    write_lambda_ssh_banner_readiness_policy,
)
from decodilo.lambda_cloud.upload_readiness_policy import (
    build_lambda_upload_readiness_gate_policy_from_path,
)


def test_upload_readiness_gate_requires_banner_before_scp(tmp_path) -> None:
    banner = tmp_path / "banner.json"
    write_lambda_ssh_banner_readiness_policy(
        banner,
        build_lambda_ssh_banner_readiness_policy(),
    )

    policy = build_lambda_upload_readiness_gate_policy_from_path(banner_policy=banner)

    assert policy.gate_policy_status == "policy_defined"
    assert policy.host_discovery_required is True
    assert policy.tcp_22_reachable_required is True
    assert policy.ssh_banner_readiness_required is True
    assert policy.upload_before_readiness_allowed is False
    assert policy.upload_failure_retry_allowed is False
    assert policy.max_source_upload_attempts == 1
    assert policy.max_dependency_upload_attempts == 1
    assert policy.launch_ready is False
    assert policy.launch_allowed is False
