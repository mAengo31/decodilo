from pydantic import ValidationError

from decodilo.lambda_cloud.first_launch_runbook import (
    LambdaFirstLaunchRunbook,
    build_lambda_first_launch_runbook,
)


def test_runbook_contains_required_non_executable_steps():
    runbook = build_lambda_first_launch_runbook()
    sections = {step.section for step in runbook.steps}

    assert "preconditions" in sections
    assert "mandatory termination sequence" in sections
    assert runbook.executable_launch_command_present is False
    assert all(step.non_executable for step in runbook.steps)
    assert "no training workload" in runbook.constraints
    assert runbook.launch_allowed is False


def test_runbook_rejects_executable_launch_command():
    runbook = build_lambda_first_launch_runbook()

    try:
        LambdaFirstLaunchRunbook(
            steps=runbook.steps,
            executable_launch_command_present=True,
        )
    except ValidationError:
        return
    raise AssertionError("expected executable launch command to be rejected")
