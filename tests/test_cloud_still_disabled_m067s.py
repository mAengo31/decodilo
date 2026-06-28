from __future__ import annotations

from decodilo.lambda_cloud.remote_vslice_retry_authorization import (
    LambdaRemoteVSliceRetryAuthorization,
)


def test_m067s_artifacts_do_not_enable_launch_or_mutation():
    authorization = LambdaRemoteVSliceRetryAuthorization(
        authorization_status="not_authorized",
        blockers=["fresh_readonly_discovery_required"],
    )

    assert authorization.launch_ready is False
    assert authorization.launch_allowed is False
    assert authorization.billable_action_performed is False
    assert authorization.real_mutation_enabled is False
