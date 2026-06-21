from __future__ import annotations

from lambda_m053_helpers import write_m053_inputs

from decodilo.lambda_cloud.m053_report import build_lambda_m053_report_from_paths


def test_m053_report_passes_planning_package_without_operator_authorization(tmp_path):
    paths = write_m053_inputs(tmp_path, approve=False)

    report = build_lambda_m053_report_from_paths(
        scope=paths["scope"],
        risk_review=paths["risk"],
        authorization=paths["authorization"],
        runbook_preview=paths["runbook"],
    )

    assert report.report_passed is True
    assert report.operator_approval_status == "not_provided"
    assert report.m054_authorization_status == "not_authorized"
    assert report.runbook_preview_status == "blocked_not_authorized"
    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.billable_action_performed is False


def test_m053_report_records_future_authorized_review_when_operator_approved(tmp_path):
    paths = write_m053_inputs(tmp_path, approve=True)

    report = build_lambda_m053_report_from_paths(
        scope=paths["scope"],
        risk_review=paths["risk"],
        authorization=paths["authorization"],
        runbook_preview=paths["runbook"],
    )

    assert report.operator_approval_status == "approved_for_future_m054_ssh_connectivity_review"
    assert report.m054_authorization_status == "authorized_for_future_m054_ssh_connectivity_review"
    assert report.launch_allowed is False
