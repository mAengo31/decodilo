from __future__ import annotations

from lambda_m053_helpers import write_m053_inputs

from decodilo.lambda_cloud.m053a_report import build_lambda_m053a_report_from_paths


def test_m053a_keeps_cloud_launch_ssh_and_remote_execution_disabled(tmp_path):
    paths = write_m053_inputs(tmp_path, approve=True)

    report = build_lambda_m053a_report_from_paths(
        operator_approval=paths["operator"],
        risk_review=paths["risk"],
        authorization=paths["authorization"],
        runbook_preview=paths["runbook"],
    )

    assert report.ssh_now is False
    assert report.run_command_now is False
    assert report.launch_now is False
    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.billable_action_performed is False
    assert report.real_mutation_enabled is False
