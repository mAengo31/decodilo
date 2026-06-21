from __future__ import annotations

from lambda_m051_helpers import write_m051_inputs

from decodilo.lambda_cloud.m051_one_shot_arming import (
    build_lambda_m051_one_shot_arming_from_paths,
)
from decodilo.lambda_cloud.m051_operator_confirmation import (
    build_lambda_m051_operator_confirmation,
    write_lambda_m051_operator_confirmation,
)


def test_m051_one_shot_arming_is_armed_but_not_standing_launch(tmp_path):
    paths = write_m051_inputs(tmp_path)
    arming = build_lambda_m051_one_shot_arming_from_paths(
        operator_confirmation=paths["operator_confirmation_m051"],
        metadata_plan=paths["metadata_plan"],
        execution_gate=paths["execution_gate"],
        no_mutation_no_ssh_audit=paths["audit_m051"],
        bootstrap_authorization=paths["authorization"],
        response_loss_controls=paths["controls"],
        expires_minutes=15,
    )

    assert arming.arming_status == "armed_for_one_shot_m051_metadata_bootstrap"
    assert arming.one_shot_request_send_permitted is False
    assert arming.request_send_permission_delegated_to_reviewer_bridge is True
    assert arming.max_launch_attempts == 1
    assert arming.standing_launch_ready is False
    assert arming.standing_launch_allowed is False
    assert arming.launch_ready is False
    assert arming.launch_allowed is False


def test_m051_one_shot_arming_blocks_missing_confirmation(tmp_path):
    paths = write_m051_inputs(tmp_path)
    incomplete = tmp_path / "incomplete-confirmation.json"
    write_lambda_m051_operator_confirmation(
        incomplete,
        build_lambda_m051_operator_confirmation(
            confirm_metadata_only_bootstrap=True,
            acknowledge_all=False,
        ),
    )
    arming = build_lambda_m051_one_shot_arming_from_paths(
        operator_confirmation=incomplete,
        metadata_plan=paths["metadata_plan"],
        execution_gate=paths["execution_gate"],
        no_mutation_no_ssh_audit=paths["audit_m051"],
        bootstrap_authorization=paths["authorization"],
        response_loss_controls=paths["controls"],
        expires_minutes=15,
    )

    assert arming.arming_status == "not_armed"
    assert arming.blockers


def test_m051_one_shot_arming_requires_expiration(tmp_path):
    paths = write_m051_inputs(tmp_path)
    arming = build_lambda_m051_one_shot_arming_from_paths(
        operator_confirmation=paths["operator_confirmation_m051"],
        metadata_plan=paths["metadata_plan"],
        execution_gate=paths["execution_gate"],
        no_mutation_no_ssh_audit=paths["audit_m051"],
        bootstrap_authorization=paths["authorization"],
        response_loss_controls=paths["controls"],
        expires_minutes=0,
    )

    assert arming.arming_status == "not_armed"
    assert "expiration_required" in arming.blockers
