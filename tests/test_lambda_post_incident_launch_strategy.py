from lambda_m035_helpers import (
    attempt_history,
    endpoint_confidence,
    option_matrix,
    shape_strategy,
    support_request,
)

from decodilo.lambda_cloud.m035_decision_record import build_lambda_m035_decision_record
from decodilo.lambda_cloud.post_incident_launch_strategy import (
    build_lambda_post_incident_launch_strategy,
)


def test_post_incident_launch_strategy_builds_review_only_package(tmp_path):
    matrix = option_matrix(tmp_path, "medium")
    strategy = build_lambda_post_incident_launch_strategy(
        attempt_history=attempt_history(tmp_path),
        endpoint_confidence_review=endpoint_confidence(tmp_path, "medium"),
        shape_strategy_review=shape_strategy(),
        option_matrix=matrix,
        support_evidence_request=support_request(),
        decision_record=build_lambda_m035_decision_record(matrix),
    )

    assert strategy.strategy_passed is True
    assert strategy.decision_record.status == "require_support_confirmation_before_next_launch"
    assert strategy.launch_ready is False
    assert strategy.launch_allowed is False
