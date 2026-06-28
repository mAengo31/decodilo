from __future__ import annotations

from decodilo.lambda_cloud.remote_vertical_slice_policy import (
    _wait_for_ssh_banner_ready,
)
from decodilo.lambda_cloud.ssh_banner_readiness_policy import (
    build_lambda_ssh_banner_readiness_policy,
)


def test_ssh_banner_policy_rejects_tcp_only_upload_readiness() -> None:
    policy = build_lambda_ssh_banner_readiness_policy()

    assert policy.policy_status == "policy_defined"
    assert policy.tcp_22_reachability_sufficient_for_upload is False
    assert policy.banner_readiness_required_before_upload is True
    assert policy.raw_tcp_banner_probe_allowed is True
    assert policy.remote_command_allowed is False
    assert policy.file_transfer_allowed_during_probe is False
    assert policy.launch_ready is False
    assert policy.launch_allowed is False


def test_wait_for_ssh_banner_requires_ssh_protocol_prefix() -> None:
    banners = iter(["not-ready", "SSH-2.0-OpenSSH_9.0"])

    readiness = _wait_for_ssh_banner_ready(
        host="203.0.113.10",
        timeout_seconds=1.0,
        interval_seconds=0.0,
        read_timeout_seconds=0.1,
        reader=lambda _host, _port, _timeout: next(banners),
        sleep_func=lambda _seconds: None,
    )

    assert readiness.ready is True
    assert readiness.poll_count == 2
    assert readiness.banner_prefix_observed is True


def test_wait_for_ssh_banner_times_out_without_prefix() -> None:
    readiness = _wait_for_ssh_banner_ready(
        host="203.0.113.10",
        timeout_seconds=0.0,
        interval_seconds=0.0,
        read_timeout_seconds=0.1,
        reader=lambda _host, _port, _timeout: "HTTP/1.1 200 OK",
        sleep_func=lambda _seconds: None,
    )

    assert readiness.ready is False
    assert readiness.poll_count == 1
    assert readiness.banner_prefix_observed is False
