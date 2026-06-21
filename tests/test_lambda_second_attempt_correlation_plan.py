import pytest
from lambda_m030_helpers import m029_authorization_package, prior_m029_report

from decodilo.lambda_cloud.second_attempt_correlation_plan import (
    LambdaSecondAttemptCorrelationPlan,
    build_lambda_second_attempt_correlation_plan,
)


def test_valid_second_attempt_correlation_plan():
    plan = build_lambda_second_attempt_correlation_plan(
        prior_m029_report=prior_m029_report(),
        m029_authorization=m029_authorization_package(),
    )

    assert plan.plan_passed is True
    assert plan.planned_shape == "gpu_8x_h100_sxm"
    assert plan.idempotency_key != plan.prior_idempotency_key
    assert plan.launch_allowed is False


def test_duplicate_idempotency_key_rejected():
    plan = build_lambda_second_attempt_correlation_plan(
        prior_m029_report=prior_m029_report(),
        m029_authorization=m029_authorization_package(),
    )

    with pytest.raises(ValueError):
        LambdaSecondAttemptCorrelationPlan(
            **{
                **plan.model_dump(mode="json"),
                "idempotency_key": plan.prior_idempotency_key,
            }
        )


def test_missing_planned_shape_rejected():
    plan = build_lambda_second_attempt_correlation_plan(
        prior_m029_report=prior_m029_report(),
        m029_authorization=m029_authorization_package(),
    )

    with pytest.raises(ValueError):
        LambdaSecondAttemptCorrelationPlan(
            **{**plan.model_dump(mode="json"), "planned_shape": ""}
        )
