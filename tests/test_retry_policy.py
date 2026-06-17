import pytest

from decodilo.storage.backend_metrics import BackendMetrics
from decodilo.storage.retry_policy import RetryPolicy, run_with_retries


def test_retry_policy_retries_retryable_errors() -> None:
    attempts = {"count": 0}
    metrics = BackendMetrics()

    def op() -> str:
        attempts["count"] += 1
        if attempts["count"] < 2:
            raise OSError("try again")
        return "ok"

    assert run_with_retries(op, policy=RetryPolicy(max_attempts=2), metrics=metrics) == "ok"
    assert metrics.backend_retries == 1


def test_retry_policy_fails_after_max_attempts() -> None:
    with pytest.raises(OSError):
        run_with_retries(
            lambda: (_ for _ in ()).throw(OSError("nope")),
            policy=RetryPolicy(max_attempts=2),
        )
