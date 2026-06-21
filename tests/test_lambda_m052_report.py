from __future__ import annotations

from lambda_m052_helpers import write_m052_inputs

from decodilo.lambda_cloud.m052_report import build_lambda_m052_report_from_paths


def test_m052_report_passes_for_clean_metadata_bootstrap_closeout(tmp_path):
    paths = write_m052_inputs(tmp_path)

    report = build_lambda_m052_report_from_paths(
        success_record=paths["success"],
        reconciliation=paths["reconciliation"],
        closeout=paths["closeout"],
        no_remote_execution_attestation=paths["attestation"],
        comparison=paths["comparison"],
        strategy_update=paths["strategy"],
        decision=paths["decision"],
    )

    assert report.report_passed is True
    assert report.success_record_status == "metadata_bootstrap_success"
    assert report.closeout_status in {"closed_success", "closed_with_warnings"}
    assert report.m053_decision == "plan_ssh_connectivity_only_review"
    assert report.historical_billable_action_performed is True
    assert report.billable_action_performed is False
    assert report.launch_ready is False
    assert report.launch_allowed is False
