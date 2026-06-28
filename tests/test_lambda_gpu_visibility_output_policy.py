from __future__ import annotations

from decodilo.lambda_cloud.gpu_visibility_output_policy import (
    build_lambda_gpu_visibility_output_policy,
)


def test_gpu_visibility_output_policy_is_bounded_and_future_only():
    policy = build_lambda_gpu_visibility_output_policy()

    assert policy.output_policy_status == "gpu_visibility_output_policy_defined_future_only"
    assert policy.allowed_fields == ["name", "memory.total", "driver_version"]
    assert policy.max_stdout_bytes == 4096
    assert policy.max_stderr_bytes == 4096
    assert policy.command_output_allowed_now is False
    assert policy.launch_ready is False
    assert policy.launch_allowed is False
