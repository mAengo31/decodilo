from __future__ import annotations

import re

from decodilo.lambda_cloud.python_runtime_output_policy import (
    LambdaPythonRuntimeOutputPolicy,
    build_lambda_python_runtime_output_policy,
)


def test_python_runtime_output_policy_is_bounded_and_future_only():
    policy = build_lambda_python_runtime_output_policy()

    assert policy.output_policy_status == "python_runtime_output_policy_defined_future_only"
    assert policy.max_stdout_bytes == 1024
    assert re.compile(policy.expected_stdout_regex).match("Python 3.12.1")
    assert policy.launch_ready is False
    assert policy.launch_allowed is False


def test_python_runtime_output_policy_rejects_unbounded_output():
    import pytest

    with pytest.raises(ValueError):
        LambdaPythonRuntimeOutputPolicy(
            output_policy_status="python_runtime_output_policy_defined_future_only",
            max_stdout_bytes=8192,
        )
