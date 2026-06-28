from __future__ import annotations

from lambda_m062_helpers import write_m062_chain

from decodilo.lambda_cloud.m062_report import build_lambda_m062_report_from_paths


def test_m062_report_passes_clean_chain(tmp_path):
    paths = write_m062_chain(tmp_path)

    report = build_lambda_m062_report_from_paths(
        success_record=paths["success"],
        reconciliation=paths["reconciliation"],
        evidence_package=paths["evidence"],
        closeout=paths["closeout"],
        command_policy=paths["command_policy"],
        output_policy=paths["output_policy"],
        command_review=paths["command_review"],
        authorization=paths["authorization"],
        runbook_preview=paths["runbook"],
    )

    assert report.report_passed is True
    assert report.success_record_status == "whoami_command_success"
    assert (
        report.m063_authorization_status
        == "authorized_for_future_m063_gpu_visibility_query_review"
    )
    assert report.historical_billable_action_performed is True
    assert report.billable_action_performed is False
    assert report.launch_ready is False
    assert report.launch_allowed is False
