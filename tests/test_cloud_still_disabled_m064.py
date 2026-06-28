from __future__ import annotations

from lambda_m064_helpers import write_m064_chain

from decodilo.lambda_cloud.m064_report import build_lambda_m064_report_from_paths


def test_m064_chain_never_enables_launch_or_current_spend(tmp_path):
    paths = write_m064_chain(tmp_path)

    report = build_lambda_m064_report_from_paths(
        success_record=paths["success"],
        parsed_output_audit=paths["parsed_audit"],
        reconciliation=paths["reconciliation"],
        closeout=paths["closeout"],
        python_command_policy=paths["python_command_policy"],
        python_output_policy=paths["python_output_policy"],
        python_command_review=paths["python_command_review"],
        authorization=paths["authorization"],
        runbook_preview=paths["runbook"],
    )

    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.billable_action_performed is False
    assert report.m064_billable_action_performed is False
