from lambda_m035_helpers import option_matrix

from decodilo.lambda_cloud.m035_decision_record import build_lambda_m035_decision_record


def test_decision_requires_support_when_endpoint_medium(tmp_path):
    record = build_lambda_m035_decision_record(option_matrix(tmp_path, "medium"))

    assert record.status == "require_support_confirmation_before_next_launch"
    assert record.launch_ready is False
    assert record.launch_allowed is False


def test_decision_prefers_lower_cost_when_endpoint_high(tmp_path):
    record = build_lambda_m035_decision_record(option_matrix(tmp_path, "high"))

    assert record.status == "authorize_future_m036_lower_cost_shape_reauthorization"


def test_decision_can_authorize_future_same_shape_with_explicit_risk_acceptance(tmp_path):
    record = build_lambda_m035_decision_record(
        option_matrix(tmp_path, "medium"),
        operator_explicitly_accepts_medium_endpoint_risk=True,
        operator_prefers_current_shape=True,
    )

    assert record.status == "authorize_future_m036_fourth_attempt_same_shape"


def test_forbidden_decision_status_rejected():
    from decodilo.lambda_cloud.m035_decision_record import LambdaM035DecisionRecord

    try:
        LambdaM035DecisionRecord(status="launch_now", recommended_option="x")  # type: ignore[arg-type]
    except ValueError:
        pass
    else:  # pragma: no cover
        raise AssertionError("launch_now must be rejected")
