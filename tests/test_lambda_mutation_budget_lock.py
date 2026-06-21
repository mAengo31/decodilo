from lambda_m024_helpers import write_m024_prepare_inputs
from pydantic import ValidationError

from decodilo.lambda_cloud.mutation_budget_lock import (
    LambdaMutationBudgetLock,
    build_lambda_mutation_budget_lock,
)


def test_valid_budget_lock_serializes(tmp_path) -> None:
    refs = write_m024_prepare_inputs(tmp_path)
    lock = build_lambda_mutation_budget_lock(
        m020_report=refs["m020"],
        approval_manifest_hash="approval",
    )

    assert lock.locked is True
    assert lock.max_budget <= 50
    assert lock.launch_allowed is False
    assert '"billable_action_performed": false' in lock.to_json()


def test_over_budget_lock_rejected() -> None:
    try:
        LambdaMutationBudgetLock(
            run_id="run",
            max_budget=51,
            max_runtime_minutes=30,
            max_instances=1,
            selected_price_record_id="price",
            price_snapshot_id="snapshot",
            safety_buffer_adjusted_cost=10,
            approval_manifest_hash="approval",
            lock_hash="hash",
        )
    except ValidationError as exc:
        assert "$50" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("over-budget lock accepted")


def test_expired_lock_invalid() -> None:
    try:
        LambdaMutationBudgetLock(
            run_id="run",
            max_budget=50,
            max_runtime_minutes=30,
            max_instances=1,
            selected_price_record_id="price",
            price_snapshot_id="snapshot",
            safety_buffer_adjusted_cost=10,
            approval_manifest_hash="approval",
            lock_hash="hash",
            expires_at_utc="2000-01-01T00:00:00Z",
        )
    except ValidationError as exc:
        assert "expired" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expired lock accepted")
