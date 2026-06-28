from __future__ import annotations

from lambda_m064_helpers import write_m064_chain

from decodilo.lambda_cloud.m065_python_runtime_authorization import (
    LambdaM065PythonRuntimeAuthorization,
    build_lambda_m065_python_runtime_authorization_from_paths,
)


def test_m065_python_runtime_authorization_accepts_hash_only_gpu_closeout(tmp_path):
    paths = write_m064_chain(tmp_path)

    authorization = build_lambda_m065_python_runtime_authorization_from_paths(
        gpu_visibility_closeout=paths["closeout"],
        command_policy=paths["python_command_policy"],
        output_policy=paths["python_output_policy"],
        command_review=paths["python_command_review"],
    )

    assert (
        authorization.authorization_status
        == "authorized_for_future_m065_python_version_query_review"
    )
    assert authorization.selected_command == "python3 --version"
    assert authorization.command_authorized_now is False
    assert authorization.launch_ready is False
    assert authorization.launch_allowed is False


def test_m065_python_runtime_authorization_rejects_immediate_flags():
    import pytest

    with pytest.raises(ValueError):
        LambdaM065PythonRuntimeAuthorization(
            authorization_status="authorized_for_future_m065_python_version_query_review",
            selected_future_command_set=[],
            command_authorized_now=True,
        )
