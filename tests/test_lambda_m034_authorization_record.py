import pytest
from pydantic import ValidationError

from decodilo.lambda_cloud.m034_authorization_record import (
    LambdaM034AuthorizationRecord,
    build_lambda_m034_authorization_record,
)


def test_m034_authorization_record_builds_for_future_review_only():
    record = build_lambda_m034_authorization_record(
        status="authorized_for_future_m034_third_launch_attempt"
    )

    assert record.status == "authorized_for_future_m034_third_launch_attempt"
    assert record.launch_authorized_now is False
    assert record.launch_ready is False
    assert record.launch_allowed is False


def test_blocked_record_is_not_authorized():
    record = build_lambda_m034_authorization_record(
        status="not_authorized",
        blockers=["missing_endpoint_confirmation"],
    )

    assert record.status == "not_authorized"
    assert record.authorized_operations == []


def test_forbidden_launch_status_rejected():
    with pytest.raises(ValidationError):
        LambdaM034AuthorizationRecord(
            status="launch_allowed",
            launch_ready=False,
            launch_allowed=False,
        )
