from __future__ import annotations

from lambda_m054a_helpers import write_m054a_inputs

from decodilo.lambda_cloud.m054a_report import build_lambda_m054a_report_from_paths


def test_m054a_report_passes_future_ssh_connectivity_package(tmp_path):
    paths = write_m054a_inputs(tmp_path)

    report = build_lambda_m054a_report_from_paths(
        execution_plan=paths["execution_plan"],
        static_validation=paths["static_validation"],
        reviewer_bridge=paths["reviewer_bridge"],
        no_exec_audit=paths["no_exec_audit"],
        command_preview=paths["command_preview"],
    )

    assert report.report_passed is True
    assert report.execution_plan_status == "plan_defined"
    assert report.static_validation_status == "passed"
    assert report.reviewer_bridge_status == "reviewer_compatible_one_shot_ready"
    assert report.no_exec_audit_status == "passed"
    assert report.command_preview_status == "ready_for_future_m054b_ssh_connectivity_review"
    assert report.future_m054b_cli_flags_accepted is True
    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.billable_action_performed is False
