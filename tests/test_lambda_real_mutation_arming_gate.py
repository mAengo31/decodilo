from pydantic import ValidationError

from decodilo.lambda_cloud.real_mutation_arming_gate import (
    LambdaRealMutationArmingGateDesign,
    build_lambda_real_mutation_arming_gate_design,
    evaluate_lambda_real_mutation_arming_gate,
)


def test_arming_gate_missing_criterion_blocks() -> None:
    report = evaluate_lambda_real_mutation_arming_gate(completed_criteria={"max_budget"})

    assert report.arming_gate_status == "design_only"
    assert report.armed is False
    assert report.blockers
    assert report.launch_allowed is False


def test_complete_arming_criteria_still_design_only() -> None:
    gate = build_lambda_real_mutation_arming_gate_design()
    completed = {criterion.criterion_id for criterion in gate.criteria}
    report = evaluate_lambda_real_mutation_arming_gate(
        completed_criteria=completed,
        gate=gate,
    )

    assert report.missing_criteria == []
    assert report.arming_gate_status == "design_only"
    assert report.real_mutation_enabled is False


def test_arming_gate_cannot_arm() -> None:
    try:
        LambdaRealMutationArmingGateDesign(criteria=[], armed=True)
    except ValidationError as exc:
        assert "cannot arm" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("arming gate armed")
