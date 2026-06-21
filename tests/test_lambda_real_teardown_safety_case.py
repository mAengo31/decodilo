from pydantic import ValidationError

from decodilo.lambda_cloud.real_teardown_safety_case import (
    LambdaRealTeardownSafetyCase,
    build_lambda_real_teardown_safety_case,
)


def test_real_teardown_safety_case_is_design_only() -> None:
    safety = build_lambda_real_teardown_safety_case()

    assert safety.design_only is True
    assert safety.real_termination_code_implemented is False
    assert safety.launch_allowed is False
    assert any("owned instance" in claim for claim in safety.claims)


def test_real_teardown_safety_case_rejects_enabled_state() -> None:
    safety = build_lambda_real_teardown_safety_case()

    try:
        LambdaRealTeardownSafetyCase(
            **safety.model_copy(update={"real_termination_code_implemented": True}).model_dump()
        )
    except ValidationError as exc:
        assert "design-only" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("teardown implementation accepted")
