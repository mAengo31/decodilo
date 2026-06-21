from lambda_m036_helpers import endpoint_upgrade, lower_cost_review

from decodilo.lambda_cloud.endpoint_confidence_upgrade import (
    LambdaEndpointConfidenceUpgradeReport,
)
from decodilo.lambda_cloud.m036_strategy_decision import (
    build_lambda_m036_strategy_decision,
)


def test_high_endpoint_and_lower_cost_recommends_reauthorization():
    report = build_lambda_m036_strategy_decision(
        endpoint_upgrade=endpoint_upgrade(),
        lower_cost_shape=lower_cost_review(),
    )

    assert report.status == "reauthorize_lower_cost_shape_before_next_launch"
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_medium_endpoint_requires_more_support_evidence():
    upgrade = LambdaEndpointConfidenceUpgradeReport(
        upgraded_confidence="medium",
        upgrade_passed=False,
        blockers=["ambiguous_response_semantics_missing"],
    )

    report = build_lambda_m036_strategy_decision(
        endpoint_upgrade=upgrade,
        lower_cost_shape=lower_cost_review(),
    )

    assert report.status == "require_more_support_evidence"


def test_operator_can_keep_current_shape_with_risk_acceptance():
    report = build_lambda_m036_strategy_decision(
        endpoint_upgrade=endpoint_upgrade(),
        lower_cost_shape=lower_cost_review(),
        operator_keeps_current_shape=True,
    )

    assert report.status == "keep_current_shape_with_operator_risk_acceptance"
