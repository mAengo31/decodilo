from lambda_m037_helpers import (
    m037_decision,
    reauth_package,
    shape_selection,
    support_package,
)

from decodilo.lambda_cloud.endpoint_confidence_decision import (
    LambdaEndpointConfidenceDecision,
)
from decodilo.lambda_cloud.m037_decision_record import (
    build_lambda_m037_decision_record,
)


def test_missing_response_requires_more_support_evidence():
    record = build_lambda_m037_decision_record()

    assert record.status == "require_more_support_evidence"
    assert record.launch_ready is False
    assert record.launch_allowed is False


def test_complete_endpoint_and_lower_cost_selects_reauthorization(tmp_path):
    record = m037_decision(tmp_path)

    assert record.status == "endpoint_confirmed_reauthorize_lower_cost_shape"


def test_endpoint_contradiction_requires_implementation_fix(tmp_path):
    endpoint = LambdaEndpointConfidenceDecision(
        status="endpoint_behavior_contradicts_current_implementation",
        confidence="high",
        blockers=["endpoint_behavior_contradicts_current_implementation"],
    )
    record = build_lambda_m037_decision_record(
        support_evidence_package=support_package(tmp_path),
        endpoint_decision=endpoint,
        shape_selection=shape_selection(),
        reauthorization_package=reauth_package(),
    )

    assert record.status == "endpoint_contradiction_fix_implementation_first"

