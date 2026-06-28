from __future__ import annotations

from lambda_m064_helpers import write_m064_chain

from decodilo.lambda_cloud.m064_report import build_lambda_m064_report_from_paths


def test_m064_report_passes_hash_only_gpu_visibility_chain(tmp_path):
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

    assert report.report_passed is True
    assert report.gpu_visibility_success_status == "gpu_visibility_query_executed_output_hash_only"
    assert report.parsed_output_audit_status == "output_hash_only"
    assert report.closeout_status == "closed_with_warnings"
    assert (
        report.m065_authorization_status
        == "authorized_for_future_m065_python_version_query_review"
    )
    assert report.historical_billable_action_performed is True
    assert report.billable_action_performed is False
    assert report.launch_ready is False
    assert report.launch_allowed is False
