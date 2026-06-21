from decodilo.lambda_cloud.launch_response_capture_policy import (
    LambdaLaunchResponseCapturePolicy,
    build_lambda_launch_response_capture_policy,
)


def test_default_capture_policy_records_metadata_only():
    policy = build_lambda_launch_response_capture_policy()

    assert policy.policy_passed is True
    assert policy.capture_http_status is True
    assert policy.capture_raw_response_body is False
    assert policy.capture_secret_values is False


def test_raw_body_capture_is_rejected():
    policy = LambdaLaunchResponseCapturePolicy(capture_raw_response_body=True)

    assert policy.policy_passed is False
    assert "raw response body capture is forbidden" in policy.blockers
