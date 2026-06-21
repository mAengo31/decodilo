from __future__ import annotations

from lambda_m053_helpers import write_m053_inputs

from decodilo.lambda_cloud.m053_report import build_lambda_m053_report_from_paths


def test_m053_keeps_cloud_launch_and_ssh_disabled(tmp_path):
    paths = write_m053_inputs(tmp_path, approve=True)

    report = build_lambda_m053_report_from_paths(
        scope=paths["scope"],
        risk_review=paths["risk"],
        authorization=paths["authorization"],
        runbook_preview=paths["runbook"],
    )

    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.billable_action_performed is False
    assert report.real_mutation_enabled is False
    assert report.m054_authorization_status == "authorized_for_future_m054_ssh_connectivity_review"
