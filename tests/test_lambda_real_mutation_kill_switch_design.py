from pydantic import ValidationError

from decodilo.lambda_cloud.real_mutation_kill_switch_design import (
    LambdaEmergencyTeardownDesign,
    build_lambda_kill_switch_design,
)


def test_kill_switch_design_requires_safety_inputs() -> None:
    design = build_lambda_kill_switch_design()

    assert design.resource_ledger_path_required is True
    assert design.max_runtime_deadline_required is True
    assert design.termination_verification_required is True
    assert design.emergency_teardown.executable_terminate_command is None
    assert design.launch_allowed is False


def test_kill_switch_rejects_executable_terminate_command() -> None:
    try:
        LambdaEmergencyTeardownDesign(executable_terminate_command="lambda terminate fake")
    except ValidationError as exc:
        assert "executable termination" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("executable termination command accepted")


def test_kill_switch_serializes() -> None:
    assert '"design_only": true' in build_lambda_kill_switch_design().to_json()
