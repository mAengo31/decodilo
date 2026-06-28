from __future__ import annotations

from decodilo.lambda_cloud.gpu_visibility_command_policy import (
    M063_GPU_VISIBILITY_COMMAND,
    build_lambda_gpu_visibility_command_policy,
    validate_gpu_visibility_command,
)


def test_gpu_visibility_command_policy_allows_exact_future_query_only():
    policy = build_lambda_gpu_visibility_command_policy()

    assert (
        policy.command_policy_status
        == "gpu_visibility_command_policy_defined_future_only"
    )
    assert policy.selected_future_command_set == [M063_GPU_VISIBILITY_COMMAND]
    assert validate_gpu_visibility_command(M063_GPU_VISIBILITY_COMMAND) is True
    assert policy.command_execution_allowed_now is False
    assert policy.launch_ready is False
    assert policy.launch_allowed is False


def test_gpu_visibility_command_policy_rejects_raw_loop_and_chaining():
    assert validate_gpu_visibility_command("nvidia-smi") is False
    assert validate_gpu_visibility_command(f"{M063_GPU_VISIBILITY_COMMAND} -l 1") is False
    assert validate_gpu_visibility_command(f"{M063_GPU_VISIBILITY_COMMAND}; whoami") is False
