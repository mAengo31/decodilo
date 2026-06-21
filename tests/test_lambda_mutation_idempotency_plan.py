from pydantic import ValidationError

from decodilo.lambda_cloud.mutation_idempotency_plan import (
    LambdaMutationIdempotencyKey,
    build_lambda_mutation_idempotency_plan,
)


def test_missing_idempotency_key_invalid() -> None:
    try:
        LambdaMutationIdempotencyKey(
            run_id="run",
            operation="launch_one_instance",
            plan_hash="plan",
            owned_resource_scope="scope",
            key="",
        )
    except ValidationError as exc:
        assert "key" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("empty idempotency key accepted")


def test_deterministic_key_repeats_for_same_inputs() -> None:
    first = build_lambda_mutation_idempotency_plan(
        run_id="run",
        operation="launch_one_instance",
        plan_hash="plan-a",
    )
    second = build_lambda_mutation_idempotency_plan(
        run_id="run",
        operation="launch_one_instance",
        plan_hash="plan-a",
    )

    assert first.idempotency_key.key == second.idempotency_key.key
    assert first.launch_allowed is False


def test_idempotency_key_changes_when_plan_hash_changes() -> None:
    first = build_lambda_mutation_idempotency_plan(
        run_id="run",
        operation="launch_one_instance",
        plan_hash="plan-a",
    )
    second = build_lambda_mutation_idempotency_plan(
        run_id="run",
        operation="launch_one_instance",
        plan_hash="plan-b",
    )

    assert first.idempotency_key.key != second.idempotency_key.key
