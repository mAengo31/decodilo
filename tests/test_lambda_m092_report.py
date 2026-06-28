from __future__ import annotations

from lambda_m092_helpers import write_m092_chain

from decodilo.lambda_cloud.m092_report import build_lambda_m092_report_from_paths


def test_m092_report_passes_for_future_authorized_tiny_training(tmp_path):
    paths = write_m092_chain(tmp_path)

    report = build_lambda_m092_report_from_paths(
        readiness=paths["readiness"],
        command_discovery=paths["discovery"],
        policy=paths["policy"],
        authorization=paths["authorization"],
        runbook_preview=paths["preview"],
    )

    assert report.report_passed is True
    assert report.tiny_real_training_command_added is True
    assert report.real_training_mechanics_exercised is True
    assert report.discovery_status == "found_safe_tiny_real_training_command"
    assert report.policy_status == "policy_passed"
    assert (
        report.m093r_authorization_status
        == "authorized_for_future_m093r_tiny_real_training_smoke"
    )
    assert report.torch_required is False
    assert report.gpu_required is False
    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report.billable_action_performed is False
