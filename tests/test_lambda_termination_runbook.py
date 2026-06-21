from pydantic import ValidationError

from decodilo.lambda_cloud.termination_runbook import (
    LambdaTerminationRunbook,
    build_lambda_termination_runbook,
)


def test_termination_runbook_is_non_executable_and_requires_owned_source():
    runbook = build_lambda_termination_runbook()

    assert runbook.owned_instance_id_source
    assert "OS shutdown is insufficient" in runbook.os_shutdown_insufficient_statement
    assert runbook.executable_terminate_command_present is False
    assert runbook.launch_allowed is False


def test_termination_runbook_rejects_executable_command():
    runbook = build_lambda_termination_runbook()

    try:
        LambdaTerminationRunbook(
            owned_instance_id_source=runbook.owned_instance_id_source,
            steps=runbook.steps,
            os_shutdown_insufficient_statement=runbook.os_shutdown_insufficient_statement,
            executable_terminate_command_present=True,
        )
    except ValidationError:
        return
    raise AssertionError("expected executable terminate command to be rejected")
