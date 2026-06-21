from lambda_m035_helpers import (
    attempt_history,
    endpoint_confidence,
    option_matrix,
    shape_strategy,
    support_request,
)

from decodilo.lambda_cloud.m035_decision_record import build_lambda_m035_decision_record
from decodilo.lambda_cloud.m035_report import build_lambda_m035_report


def test_m035_report_serializes_and_keeps_flags_false(tmp_path):
    matrix = option_matrix(tmp_path, "medium")
    report = build_lambda_m035_report(
        attempt_history=attempt_history(tmp_path),
        endpoint_confidence_review=endpoint_confidence(tmp_path, "medium"),
        shape_strategy_review=shape_strategy(),
        option_matrix=matrix,
        support_evidence_request=support_request(),
        decision_record=build_lambda_m035_decision_record(matrix),
    )

    assert report.report_passed is True
    assert report.decision_record.status == "require_support_confirmation_before_next_launch"
    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert "launch_allowed\": true" not in report.to_json()
