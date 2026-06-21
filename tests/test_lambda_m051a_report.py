from __future__ import annotations

from lambda_m051_helpers import write_m051_inputs

from decodilo.lambda_cloud.m051a_report import build_lambda_m051a_report_from_paths


def test_m051a_report_passes_complete_bridge_chain(tmp_path):
    paths = write_m051_inputs(tmp_path)

    report = build_lambda_m051a_report_from_paths(
        operator_confirmation=paths["operator_confirmation_m051"],
        arming=paths["one_shot_arming_m051"],
        reviewer_bridge=paths["reviewer_bridge_m051"],
        arming_gate=paths["arming_gate_m051"],
        command_preview=paths["arming_command_preview_m051"],
    )

    assert report.report_passed is True
    assert report.operator_confirmation_status == (
        "confirmed_for_m051_one_shot_metadata_bootstrap"
    )
    assert report.one_shot_arming_status == "armed_for_one_shot_m051_metadata_bootstrap"
    assert report.command_binding_status == "passed"
    assert report.artifact_binding_status == "passed"
    assert report.reviewer_bridge_status == "reviewer_compatible_one_shot_ready"
    assert report.arming_gate_status == "passed"
    assert report.one_shot_request_send_permitted_in_bridge is True
    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.billable_action_performed is False
