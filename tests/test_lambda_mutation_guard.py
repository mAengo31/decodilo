from decodilo.lambda_cloud.mutation_guard import (
    MUTATING_OPERATIONS,
    READ_ONLY_OPERATIONS,
    LambdaMutationGuard,
)


def test_mutation_guard_allows_reads_and_denies_mutations() -> None:
    guard = LambdaMutationGuard()

    assert all(guard.check(operation).allowed for operation in READ_ONLY_OPERATIONS)
    assert all(not guard.check(operation).allowed for operation in MUTATING_OPERATIONS)
    assert guard.check("unknown_operation").allowed is False
    assert guard.check("launch_instance").to_json()
