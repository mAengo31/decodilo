from lambda_m044_helpers import write_m044_inputs

from decodilo.lambda_cloud.m044_report import build_lambda_m044_report_from_paths


def test_m044_report_passes_for_accepted_future_review(tmp_path):
    paths = write_m044_inputs(tmp_path)
    report = build_lambda_m044_report_from_paths(
        cost_review=paths["cost"],
        risk_acceptance=paths["risk"],
        operator_decision=paths["operator"],
        decision=paths["decision_m044"],
        authorization=paths["authorization_m045"],
        command_preview=paths["preview_m045"],
        wait_plan=paths["wait"],
    )

    assert report.report_passed is True
    assert report.decision_status == "authorize_future_m045_catalog_rotation_launch_review"
    assert report.future_review_allowed is True
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_m044_report_blocks_incomplete_operator_decision(tmp_path):
    paths = write_m044_inputs(tmp_path, accept=False)
    report = build_lambda_m044_report_from_paths(
        cost_review=paths["cost"],
        risk_acceptance=paths["risk"],
        operator_decision=paths["operator"],
        decision=paths["decision_m044"],
        authorization=paths["authorization_m045"],
        command_preview=paths["preview_m045"],
        wait_plan=paths["wait"],
    )

    assert report.report_passed is False
    assert report.risk_acceptance_status == "not_provided"
    assert "catalog_rotation_operator_decision_not_provided" in report.blockers
