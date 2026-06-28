from __future__ import annotations

import pytest

from decodilo.lambda_cloud.remote_command_stage_policy import (
    LambdaRemoteCommandStagePolicy,
    build_lambda_remote_command_stage_policy,
)


def test_remote_command_stage_policy_sets_noop_as_current_stage():
    policy = build_lambda_remote_command_stage_policy()

    assert policy.policy_status == "policy_defined"
    assert policy.current_accepted_stage == "noop_command_only"
    assert policy.allowed_future_review_stages == ["identity_command"]
    assert policy.training_command_allowed is False
    assert policy.package_install_allowed is False
    assert policy.launch_ready is False
    assert policy.launch_allowed is False


def test_remote_command_stage_policy_rejects_training_stage():
    with pytest.raises(ValueError, match="training command"):
        LambdaRemoteCommandStagePolicy(
            allowed_future_review_stages=["training_command"],
        )
