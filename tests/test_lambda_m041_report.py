from lambda_m041_helpers import write_m041_inputs

from decodilo.lambda_cloud.m041_report import build_lambda_m041_report_from_paths


def test_m041_report_acceptance_path_summarizes_future_m042(tmp_path):
    paths = write_m041_inputs(tmp_path)

    report = build_lambda_m041_report_from_paths(
        risk_acceptance=paths["risk"],
        operator_decision=paths["decision"],
        m042_authorization=paths["m042"],
        gate_check=paths["gate"],
        command_preview=paths["preview"],
    )

    assert report.risk_acceptance_status == "accepted_for_future_m042_review"
    assert (
        report.m042_authorization_status
        == "authorized_for_future_m042_catalog_availability_launch_review"
    )
    assert report.gate_check_status == "passed"
    assert report.command_preview_status == "ready_for_future_m042"
    assert report.future_m042_candidate is True
    assert report.report_passed is True
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_m041_report_declined_path_uses_wait_plan(tmp_path):
    paths = write_m041_inputs(tmp_path, accepted=False)

    report = build_lambda_m041_report_from_paths(
        risk_acceptance=paths["risk"],
        operator_decision=paths["decision"],
        wait_plan=paths["wait"],
    )

    assert report.risk_acceptance_status == "declined_wait_for_live_availability"
    assert report.operator_decision_status == "wait_for_live_availability"
    assert report.wait_plan_status == "wait_for_live_availability"
    assert report.future_m042_candidate is False
    assert report.report_passed is True
