from __future__ import annotations

from lambda_m051_helpers import run_m051_fake, write_m051_inputs

from decodilo.lambda_cloud.m051_artifact_binding import (
    build_lambda_m051_artifact_binding_from_paths,
    write_lambda_m051_artifact_binding,
)
from decodilo.lambda_cloud.m051_exact_command_binding import (
    build_lambda_m051_exact_command_binding_from_paths,
    write_lambda_m051_exact_command_binding,
)
from decodilo.lambda_cloud.m051_execution_reviewer_bridge import (
    build_lambda_m051_execution_reviewer_bridge_from_paths,
)
from decodilo.lambda_cloud.m051_one_shot_arming import (
    build_lambda_m051_one_shot_arming_from_paths,
    write_lambda_m051_one_shot_arming,
)


def test_m051_reviewer_bridge_exposes_only_one_shot_permission(tmp_path):
    paths = write_m051_inputs(tmp_path)

    bridge = build_lambda_m051_execution_reviewer_bridge_from_paths(
        arming=paths["one_shot_arming_m051"],
        command_binding=paths["command_binding_m051"],
        artifact_binding=paths["artifact_binding_m051"],
    )

    assert bridge.bridge_status == "reviewer_compatible_one_shot_ready"
    assert bridge.one_shot_request_send_permitted is True
    assert bridge.max_launch_attempts == 1
    assert bridge.no_auto_retry is True
    assert bridge.no_ssh is True
    assert bridge.no_remote_commands is True
    assert bridge.launch_ready is False
    assert bridge.launch_allowed is False


def test_m051_reviewer_bridge_blocks_expired_arming(tmp_path):
    paths = write_m051_inputs(tmp_path)
    expired = build_lambda_m051_one_shot_arming_from_paths(
        operator_confirmation=paths["operator_confirmation_m051"],
        metadata_plan=paths["metadata_plan"],
        execution_gate=paths["execution_gate"],
        no_mutation_no_ssh_audit=paths["audit_m051"],
        bootstrap_authorization=paths["authorization"],
        response_loss_controls=paths["controls"],
        expires_minutes=1,
        created_at_utc="2020-01-01T00:00:00Z",
    )
    expired_path = tmp_path / "expired-arming.json"
    command_path = tmp_path / "expired-command-binding.json"
    artifact_path = tmp_path / "expired-artifact-binding.json"
    write_lambda_m051_one_shot_arming(expired_path, expired)
    write_lambda_m051_exact_command_binding(
        command_path,
        build_lambda_m051_exact_command_binding_from_paths(arming=expired_path),
    )
    write_lambda_m051_artifact_binding(
        artifact_path,
        build_lambda_m051_artifact_binding_from_paths(
            arming=expired_path,
            command_binding=command_path,
        ),
    )

    bridge = build_lambda_m051_execution_reviewer_bridge_from_paths(
        arming=expired_path,
        command_binding=command_path,
        artifact_binding=artifact_path,
    )

    assert bridge.bridge_status == "not_ready"
    assert bridge.one_shot_request_send_permitted is False
    assert "m051_one_shot_arming_expired" in bridge.blockers


def test_m029_run_rejects_m051_execution_without_reviewer_bridge(tmp_path):
    result = run_m051_fake(tmp_path, omit={"--m051-reviewer-bridge"})

    assert result.returncode != 0
    assert "m051_reviewer_bridge" in result.stderr
