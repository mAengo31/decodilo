from __future__ import annotations

import pytest

from decodilo.lambda_cloud.remote_command_stage_policy import (
    build_lambda_remote_command_stage_policy,
    write_lambda_remote_command_stage_policy,
)
from decodilo.lambda_cloud.smallest_useful_command_review import (
    LambdaSmallestUsefulCommandReview,
    build_lambda_smallest_useful_command_review_from_path,
)


def test_smallest_useful_review_selects_hostname(tmp_path):
    policy_path = tmp_path / "policy.json"
    write_lambda_remote_command_stage_policy(
        policy_path,
        build_lambda_remote_command_stage_policy(),
    )

    review = build_lambda_smallest_useful_command_review_from_path(
        stage_policy=policy_path,
    )

    assert review.review_status == "review_passed"
    assert review.recommended_next_command_stage == "identity_command"
    assert review.selected_future_command_set == ["hostname"]
    assert review.nvidia_smi_authorized is False
    assert review.launch_ready is False
    assert review.launch_allowed is False


def test_smallest_useful_review_rejects_gpu_visibility_for_m058():
    with pytest.raises(ValueError, match="identity commands"):
        LambdaSmallestUsefulCommandReview(
            review_status="review_passed",
            recommended_next_command_stage="identity_command",
            selected_future_command_set=["nvidia-smi"],
            command_risk="too_much",
        )
