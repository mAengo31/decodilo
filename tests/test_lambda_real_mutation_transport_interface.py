from pydantic import ValidationError

from decodilo.lambda_cloud.real_mutation_transport_interface import (
    LambdaRealMutationOperationRequest,
    LambdaRealMutationOperationResult,
)


def _request(**updates):
    data = {
        "operation_name": "launch_one_instance",
        "idempotency_key": "idem-1",
        "run_id": "run",
        "dry_run_plan_hash": "plan",
        "approval_manifest_hash": "approval",
        "budget_lock_hash": "budget",
        "resource_ledger_hash": "ledger",
        "teardown_plan_hash": "teardown",
        "kill_switch_plan_hash": "kill",
        "operation_spec_hash": "spec",
        "owned_resource_scope": "planned-owned-placeholder",
        "request_payload_redacted": {"operation_name": "launch_one_instance"},
    }
    data.update(updates)
    return LambdaRealMutationOperationRequest(**data)


def test_interface_models_serialize() -> None:
    request = _request()
    result = LambdaRealMutationOperationResult(operation_name="launch_one_instance")

    assert request.real_request_allowed is False
    assert result.request_constructed is False
    assert '"launch_allowed": false' in result.to_json()


def test_real_request_allowed_cannot_be_true() -> None:
    try:
        _request(real_request_allowed=True)
    except ValidationError as exc:
        assert "not allowed in M024" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("real request was allowed")


def test_missing_idempotency_key_invalid() -> None:
    try:
        _request(idempotency_key="")
    except ValidationError as exc:
        assert "idempotency_key" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("missing idempotency key accepted")


def test_request_payload_redaction_required() -> None:
    try:
        _request(request_payload_redacted={})
    except ValidationError as exc:
        assert "redacted request payload" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("unredacted request accepted")
