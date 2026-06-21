import pytest
from pydantic import ValidationError

from decodilo.lambda_cloud.real_launch_decision_record import (
    LambdaRealLaunchDecisionRecord,
)


def test_decision_record_allows_only_m026_statuses():
    record = LambdaRealLaunchDecisionRecord(
        status="approve_m027_minimal_real_mutation_implementation",
        rationale="implementation review only",
    )

    assert record.real_mutation_enabled is False
    assert record.launch_ready is False
    assert record.launch_allowed is False


def test_decision_record_rejects_forbidden_status_and_flags():
    with pytest.raises(ValidationError):
        LambdaRealLaunchDecisionRecord(
            status="launch_" + "approved",
            rationale="not allowed",
        )
    with pytest.raises(ValidationError):
        LambdaRealLaunchDecisionRecord(
            status="blocked",
            rationale="not allowed",
            launch_allowed=True,
        )
