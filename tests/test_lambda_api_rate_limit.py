from decodilo.lambda_cloud.api_rate_limit import RateLimitPolicy


def test_lambda_rate_limit_policy_retries_only_retryable_reads() -> None:
    policy = RateLimitPolicy(max_attempts=2)

    assert policy.should_retry(status_code=429, attempt=1)
    assert policy.should_retry(status_code=500, attempt=1)
    assert not policy.should_retry(status_code=401, attempt=1)
    assert not policy.should_retry(status_code=403, attempt=1)
    assert not policy.should_retry(status_code=429, attempt=2)
