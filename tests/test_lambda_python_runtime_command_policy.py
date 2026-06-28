from __future__ import annotations

from decodilo.lambda_cloud.python_runtime_command_policy import (
    M065_PYTHON_RUNTIME_COMMAND,
    build_lambda_python_runtime_command_policy,
    validate_python_runtime_command,
)


def test_python_runtime_command_policy_allows_exact_future_version_query_only():
    policy = build_lambda_python_runtime_command_policy()

    assert policy.policy_status == "python_runtime_command_policy_defined_future_only"
    assert policy.selected_future_command_set == [M065_PYTHON_RUNTIME_COMMAND]
    assert validate_python_runtime_command(M065_PYTHON_RUNTIME_COMMAND) is True
    assert policy.command_execution_allowed_now is False
    assert policy.launch_ready is False
    assert policy.launch_allowed is False


def test_python_runtime_command_policy_rejects_inline_module_and_chaining():
    assert validate_python_runtime_command("python3 -c 'print(1)'") is False
    assert validate_python_runtime_command("python3 -m pip --version") is False
    assert validate_python_runtime_command("python3 --version; whoami") is False
