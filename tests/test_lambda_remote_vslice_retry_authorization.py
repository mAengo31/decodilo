from __future__ import annotations

from decodilo.lambda_cloud.remote_vslice_retry_authorization import (
    build_lambda_remote_vslice_retry_authorization_from_path,
)
from decodilo.lambda_cloud.remote_vslice_retry_decision import (
    LambdaRemoteVSliceRetryDecision,
    write_lambda_remote_vslice_retry_decision,
)


def test_retry_authorization_is_future_only(tmp_path):
    decision_path = tmp_path / "decision.json"
    write_lambda_remote_vslice_retry_decision(
        decision_path,
        LambdaRemoteVSliceRetryDecision(
            decision_status="authorize_future_m067r2_on_ssh_proven_candidate",
            selected_candidate="gpu_1x_a10",
            selected_region="us-east-1",
        ),
    )

    authorization = build_lambda_remote_vslice_retry_authorization_from_path(
        decision=decision_path,
    )

    assert (
        authorization.authorization_status
        == "authorized_for_future_m067r2_ssh_proven_candidate_review"
    )
    assert authorization.launch_authorized_now is False
    assert authorization.launch_ready is False
    assert authorization.launch_allowed is False
