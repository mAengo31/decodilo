from datetime import datetime, timedelta, timezone

import pytest

from decodilo.lambda_cloud.launch_window_lock import (
    LambdaLaunchWindowLock,
    LambdaLaunchWindowPolicy,
    build_lambda_launch_window_lock,
)


def test_launch_window_lock_valid():
    lock = build_lambda_launch_window_lock(max_runtime_minutes=30)

    assert lock.launch_window_valid is True
    assert lock.launch_allowed is False


def test_expired_launch_window_invalid():
    expired = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    with pytest.raises(ValueError):
        build_lambda_launch_window_lock(valid_until_utc=expired)


def test_background_execution_rejected():
    with pytest.raises(ValueError):
        LambdaLaunchWindowLock(
            policy=LambdaLaunchWindowPolicy(background_execution_allowed=True),
            lock_hash="hash",
        )

