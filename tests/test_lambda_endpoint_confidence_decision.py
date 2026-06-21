from lambda_m036_helpers import endpoint_behavior, endpoint_upgrade, validation

from decodilo.lambda_cloud.endpoint_behavior_evidence import (
    LambdaEndpointBehaviorEvidence,
)
from decodilo.lambda_cloud.endpoint_confidence_decision import (
    build_lambda_endpoint_confidence_decision,
)
from decodilo.lambda_cloud.endpoint_confidence_upgrade import (
    LambdaEndpointConfidenceUpgradeReport,
)


def test_complete_response_decides_endpoint_confidence_high():
    decision = build_lambda_endpoint_confidence_decision(
        validation=validation(),
        endpoint_confidence_upgrade=endpoint_upgrade(),
        endpoint_behavior=endpoint_behavior(),
    )

    assert decision.status == "endpoint_confidence_high"
    assert decision.launch_ready is False
    assert decision.launch_allowed is False


def test_missing_ambiguous_semantics_requires_more_evidence():
    upgrade = LambdaEndpointConfidenceUpgradeReport(
        upgraded_confidence="medium",
        upgrade_passed=False,
        blockers=["ambiguous_response_semantics_missing"],
    )
    decision = build_lambda_endpoint_confidence_decision(
        validation=validation(),
        endpoint_confidence_upgrade=upgrade,
    )

    assert decision.status == "endpoint_confidence_insufficient"
    assert "ambiguous_response_semantics_missing" in decision.blockers


def test_contradicting_method_path_blocks_before_launch():
    behavior = endpoint_behavior().model_copy(update={"launch_method": "GET"})
    decision = build_lambda_endpoint_confidence_decision(
        validation=validation(),
        endpoint_confidence_upgrade=endpoint_upgrade(),
        endpoint_behavior=behavior,
    )

    assert decision.status == "endpoint_behavior_contradicts_current_implementation"


def test_medium_confidence_can_be_explicitly_accepted_for_future_review():
    upgrade = LambdaEndpointConfidenceUpgradeReport(
        upgraded_confidence="medium",
        upgrade_passed=False,
        blockers=[],
    )
    decision = build_lambda_endpoint_confidence_decision(
        validation=validation(),
        endpoint_confidence_upgrade=upgrade,
        endpoint_behavior=LambdaEndpointBehaviorEvidence.model_validate(
            endpoint_behavior().model_dump()
        ),
        operator_accepts_medium=True,
    )

    assert decision.status == "endpoint_confidence_medium_accepted"

