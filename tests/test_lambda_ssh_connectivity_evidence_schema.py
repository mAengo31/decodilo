from __future__ import annotations

from decodilo.lambda_cloud.ssh_connectivity_evidence_schema import (
    build_lambda_ssh_connectivity_evidence_schema,
    validate_ssh_connectivity_evidence_payload,
)


def test_ssh_connectivity_evidence_schema_is_valid_and_non_launching():
    report = build_lambda_ssh_connectivity_evidence_schema()

    assert report.evidence_schema_status == "schema_valid"
    assert report.remote_command_output_allowed is False
    assert report.private_key_material_allowed is False
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_ssh_connectivity_evidence_schema_rejects_command_output_and_private_key():
    blockers = validate_ssh_connectivity_evidence_payload(
        {
            "remote_command_output": "hostname",
            "private_key": "-----BEGIN OPENSSH PRIVATE KEY-----",
        }
    )

    assert "remote_command_output_present" in blockers
    assert "private_key_material_present" in blockers
    assert "missing_field:selected_instance_id_redacted" in blockers
