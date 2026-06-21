from pydantic import ValidationError

from decodilo.lambda_cloud.mutation_arming_state import (
    LambdaMutationArmingState,
    evaluate_lambda_mutation_arming_state,
)


def test_arming_state_default_unarmed() -> None:
    report = evaluate_lambda_mutation_arming_state()

    assert report.arming_state.mutation_armed is False
    assert report.arming_state_valid is True
    assert report.launch_allowed is False


def test_arming_state_cannot_arm() -> None:
    try:
        LambdaMutationArmingState(mutation_armed=True)
    except ValidationError as exc:
        assert "cannot arm" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("mutation arming state armed")
