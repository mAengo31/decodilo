from __future__ import annotations

from lambda_m053_helpers import write_m053_inputs

from decodilo.lambda_cloud.m053a_report import build_lambda_m053a_report_from_paths


def test_m053a_report_blocks_missing_operator_choice(tmp_path):
    paths = write_m053_inputs(tmp_path)

    report = build_lambda_m053a_report_from_paths(
        operator_approval=paths["operator"],
        risk_review=paths["risk"],
        authorization=paths["authorization"],
        runbook_preview=paths["runbook"],
    )

    assert report.operator_choice == "not_provided"
    assert report.report_passed is False
    assert "operator_choice_not_provided" in report.blockers
    assert report.m054_authorization_status == "not_authorized"
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_m053a_report_accepts_future_only_m054_review(tmp_path):
    paths = write_m053_inputs(tmp_path, approve=True)

    report = build_lambda_m053a_report_from_paths(
        operator_approval=paths["operator"],
        risk_review=paths["risk"],
        authorization=paths["authorization"],
        runbook_preview=paths["runbook"],
    )

    assert report.operator_choice == "approve_future_m054_ssh_connectivity_only_review"
    assert report.report_passed is True
    assert report.risk_review_status == "passed"
    assert report.m054_authorization_status == "authorized_for_future_m054_ssh_connectivity_review"
    assert report.runbook_preview_status == "ready_for_future_m054_ssh_connectivity_review"
    assert report.ssh_now is False
    assert report.run_command_now is False
    assert report.launch_now is False


def test_m053a_report_accepts_explicit_pause(tmp_path):
    paths = write_m053_inputs(tmp_path, decline=True)

    report = build_lambda_m053a_report_from_paths(
        operator_approval=paths["operator"],
        risk_review=paths["risk"],
        authorization=paths["authorization"],
        runbook_preview=paths["runbook"],
    )

    assert report.operator_choice == "pause_remote_access_keep_m054_not_authorized"
    assert report.report_passed is True
    assert report.m054_authorization_status == "not_authorized"
    assert report.runbook_preview_status == "blocked_not_authorized"
    assert report.launch_ready is False
    assert report.launch_allowed is False
