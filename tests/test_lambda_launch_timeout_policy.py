from decodilo.lambda_cloud.launch_timeout_policy import build_lambda_launch_timeout_policy


def test_valid_launch_timeout_policy_passes_review_only():
    policy = build_lambda_launch_timeout_policy()

    assert policy.policy_passed is True
    assert policy.launch_request_timeout_seconds == 30.0
    assert policy.no_auto_launch_retry is True
    assert policy.launch_ready is False
    assert policy.launch_allowed is False


def test_launch_timeout_too_low_blocks_policy():
    policy = build_lambda_launch_timeout_policy(launch_request_timeout_seconds=0.5)

    assert policy.policy_passed is False
    assert "launch_timeout_too_low_for_prior_response_loss" in policy.blockers


def test_auto_launch_retry_blocks_policy():
    policy = build_lambda_launch_timeout_policy(no_auto_launch_retry=False)

    assert policy.policy_passed is False
    assert "automatic_launch_retry_allowed" in policy.blockers
