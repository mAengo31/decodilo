from __future__ import annotations

from lambda_m051_helpers import write_m051_inputs

from decodilo.lambda_cloud.m051_bootstrap_execution_gate import (
    build_lambda_m051_bootstrap_execution_gate_from_paths,
)


def test_m051_bootstrap_execution_gate_passes_for_metadata_only_artifacts(tmp_path):
    paths = write_m051_inputs(tmp_path)

    gate = build_lambda_m051_bootstrap_execution_gate_from_paths(
        metadata_plan=paths["metadata_plan"],
        scope=paths["scope"],
        access_policy=paths["access"],
        risk_review=paths["risk"],
        authorization=paths["authorization"],
        response_loss_controls=paths["controls"],
    )

    assert gate.gate_passed is True
    assert gate.metadata_only is True
    assert gate.ssh_used is False
    assert gate.remote_commands_allowed is False
    assert gate.package_install_allowed is False
    assert gate.training_allowed is False
    assert gate.response_capture_active is True
    assert gate.no_auto_launch_retry is True
    assert gate.effective_launch_timeout_seconds >= 30
    assert gate.launch_ready is False
    assert gate.launch_allowed is False
