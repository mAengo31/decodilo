from lambda_m044g_helpers import write_m044g_inputs

from decodilo.lambda_cloud.m044g_report import load_lambda_m044g_report


def test_m044g_report_passes_for_flexible_selector_future_review(tmp_path):
    paths = write_m044g_inputs(tmp_path)
    report = load_lambda_m044g_report(paths["report"])

    assert report.report_passed is True
    assert report.future_launch_candidate is True
    assert report.selector_without_risk_status == (
        "selected_catalog_only_requires_risk_acceptance"
    )
    assert report.selector_with_risk_status == "selected_catalog_only_risk_accepted"
    assert (
        report.authorization_status
        == "authorized_for_future_flexible_selector_launch_review"
    )
    assert report.gate_check_status == "passed"
    assert report.fixed_shape_audit_status == "passed"
    assert report.command_preview_status == "ready_for_future_flexible_selector_review"
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_m044g_report_blocks_when_flexible_authorization_blocks(tmp_path):
    paths = write_m044g_inputs(tmp_path, risk_accepted=False)
    report = load_lambda_m044g_report(paths["report"])

    assert report.report_passed is False
    assert report.future_launch_candidate is False
    assert "selector_launch_selection_not_allowed" in report.blockers
