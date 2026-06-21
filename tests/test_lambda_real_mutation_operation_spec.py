from pydantic import ValidationError

from decodilo.lambda_cloud.real_mutation_operation_spec import (
    LambdaRealMutationOperationSpec,
    build_lambda_real_mutation_operation_set,
)


def test_operation_spec_marks_future_mutations_disabled() -> None:
    operation_set = build_lambda_real_mutation_operation_set()
    by_name = {operation.operation_name: operation for operation in operation_set.operations}

    assert by_name["launch_one_instance"].operation_kind == "future_mutation"
    assert by_name["launch_one_instance"].allowed_in_m023 is False
    assert by_name["terminate_owned_instance"].allowed_in_m023 is False
    assert "terminate_unowned_instance" in operation_set.explicitly_excluded
    assert "restart_instance" in operation_set.explicitly_excluded
    assert "create_ssh_key" in operation_set.explicitly_excluded
    assert operation_set.launch_allowed is False


def test_future_mutation_cannot_be_allowed_in_m023() -> None:
    try:
        LambdaRealMutationOperationSpec(
            operation_name="launch_one_instance",
            operation_kind="future_mutation",
            allowed_in_m023=True,
        )
    except ValidationError as exc:
        assert "not allowed in M023" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("future mutation was allowed")


def test_operation_spec_serializes_stable_json() -> None:
    text = build_lambda_real_mutation_operation_set().to_json()

    assert '"real_mutation_enabled": false' in text
    assert '"launch_allowed": false' in text
