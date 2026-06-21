from decodilo.lambda_cloud.final_teardown_verification_plan import (
    LambdaFinalTeardownVerificationPlan,
    build_lambda_final_teardown_verification_plan,
)


def test_final_teardown_plan_contains_required_safety_steps():
    plan = build_lambda_final_teardown_verification_plan()

    assert plan.terminate_only_owned_instance is True
    assert plan.os_shutdown_insufficient is True
    assert plan.executable_terminate_command_present is False
    assert any(step.read_only_verification for step in plan.steps)


def test_executable_terminate_command_rejected():
    try:
        LambdaFinalTeardownVerificationPlan(
            steps=[],
            executable_terminate_command_present=True,
        )
    except ValueError as exc:
        assert "executable terminate" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("executable terminate command should be rejected")

