import pytest
from pydantic import ValidationError

from decodilo.lambda_cloud.m027_authorization_record import (
    LambdaM027AuthorizationRecord,
    build_lambda_m027_authorization_record,
)
from decodilo.lambda_cloud.real_launch_decision_record import (
    LambdaRealLaunchDecisionRecord,
)


def test_authorization_record_builds_from_approved_decision():
    decision = LambdaRealLaunchDecisionRecord(
        status="approve_m027_minimal_real_mutation_implementation",
        rationale="implementation only",
    )

    record = build_lambda_m027_authorization_record(decision)

    assert record.status == "authorized_to_implement_minimal_mutation_code_disabled_by_default"
    assert "real launch execution" in record.forbidden_scope
    assert record.real_mutation_enabled is False
    assert record.launch_ready is False
    assert record.launch_allowed is False


def test_blocked_decision_not_authorized():
    decision = LambdaRealLaunchDecisionRecord(status="blocked", rationale="blocked")

    record = build_lambda_m027_authorization_record(decision)

    assert record.status == "not_authorized"
    assert record.authorized_scope == []


def test_authorization_record_rejects_forbidden_status_and_flags():
    with pytest.raises(ValidationError):
        LambdaM027AuthorizationRecord(
            decision_record_ref="decision",
            status="authorized_to_" + "launch",
        )
    with pytest.raises(ValidationError):
        LambdaM027AuthorizationRecord(
            decision_record_ref="decision",
            status="not_authorized",
            real_mutation_enabled=True,
        )
