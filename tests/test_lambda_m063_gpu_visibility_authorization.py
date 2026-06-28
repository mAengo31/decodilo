from __future__ import annotations

from lambda_m062_helpers import write_m062_chain

from decodilo.lambda_cloud.m063_gpu_visibility_authorization import (
    LambdaM063GPUVisibilityAuthorization,
    build_lambda_m063_gpu_visibility_authorization_from_paths,
)


def test_m063_gpu_visibility_authorization_is_future_only(tmp_path):
    paths = write_m062_chain(tmp_path)

    authorization = build_lambda_m063_gpu_visibility_authorization_from_paths(
        whoami_closeout=paths["closeout"],
        command_policy=paths["command_policy"],
        output_policy=paths["output_policy"],
        command_review=paths["command_review"],
    )

    assert (
        authorization.authorization_status
        == "authorized_for_future_m063_gpu_visibility_query_review"
    )
    assert authorization.command_authorized_now is False
    assert authorization.launch_ready is False
    assert authorization.launch_allowed is False


def test_m063_gpu_visibility_authorization_blocks_failed_whoami(tmp_path):
    paths = write_m062_chain(tmp_path, stdout_stored=True, stdout_redacted="ubuntu")

    authorization = build_lambda_m063_gpu_visibility_authorization_from_paths(
        whoami_closeout=paths["closeout"],
        command_policy=paths["command_policy"],
        output_policy=paths["output_policy"],
        command_review=paths["command_review"],
    )

    assert authorization.authorization_status == "not_authorized"
    assert "whoami_closeout_not_succeeded" in authorization.blockers


def test_m063_gpu_visibility_authorization_rejects_immediate_flags():
    import pytest

    with pytest.raises(ValueError):
        LambdaM063GPUVisibilityAuthorization(
            authorization_status="authorized_for_future_m063_gpu_visibility_query_review",
            selected_future_command_set=[],
            command_authorized_now=True,
        )
