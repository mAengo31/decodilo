"""Evidence schema for future SSH-connectivity-only Lambda review."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

LambdaSSHConnectivityEvidenceSchemaStatus = Literal["schema_valid", "blocked"]

REQUIRED_EVIDENCE_FIELDS = (
    "selected_instance_id_redacted",
    "selected_instance_type",
    "region",
    "ip_or_hostname_redacted",
    "ssh_client_mode",
    "selected_username",
    "host_key_policy",
    "start_timestamp",
    "connection_result",
    "auth_result",
    "no_remote_command",
    "no_file_transfer",
    "no_port_forwarding",
    "no_package_install",
    "no_training",
    "timeout_seconds",
    "controller_timeout_enforced",
    "exit_or_connection_status",
    "error_classification",
    "stderr_redacted",
    "stderr_sha256_prefix",
    "stderr_truncated",
    "termination_report",
    "final_discovery",
    "secret_scan",
)


class LambdaSSHConnectivityEvidenceSchemaReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    evidence_schema_status: LambdaSSHConnectivityEvidenceSchemaStatus
    required_fields: list[str] = Field(default_factory=lambda: list(REQUIRED_EVIDENCE_FIELDS))
    remote_command_output_allowed: bool = False
    private_key_material_allowed: bool = False
    ip_hostname_redaction_required: bool = True
    bounded_output_required: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_schema(self) -> LambdaSSHConnectivityEvidenceSchemaReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.remote_command_output_allowed
            or self.private_key_material_allowed
            or not self.ip_hostname_redaction_required
        ):
            raise ValueError(
                "SSH connectivity evidence schema cannot allow execution output or secrets"
            )
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


LambdaSSHConnectivityEvidenceSchema = LambdaSSHConnectivityEvidenceSchemaReport


def validate_ssh_connectivity_evidence_payload(payload: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    for field in REQUIRED_EVIDENCE_FIELDS:
        if field not in payload:
            blockers.append(f"missing_field:{field}")
    if payload.get("remote_command_output"):
        blockers.append("remote_command_output_present")
    serialized = json.dumps(payload, sort_keys=True)
    if "PRIVATE KEY" in serialized or "BEGIN OPENSSH" in serialized:
        blockers.append("private_key_material_present")
    if payload.get("ip_or_hostname") and not payload.get("ip_or_hostname_redacted"):
        blockers.append("ip_hostname_not_redacted")
    return sorted(set(blockers))


def build_lambda_ssh_connectivity_evidence_schema() -> LambdaSSHConnectivityEvidenceSchemaReport:
    return LambdaSSHConnectivityEvidenceSchemaReport(
        evidence_schema_status="schema_valid",
        warnings=[
            "future M054 evidence must not include remote command output",
            "private key material must never be serialized",
            "future M054 evidence must prove no shell, command, transfer, "
            "forwarding, install, or training occurred",
        ],
    )


def load_lambda_ssh_connectivity_evidence_schema(
    path: str | Path,
) -> LambdaSSHConnectivityEvidenceSchemaReport:
    return LambdaSSHConnectivityEvidenceSchemaReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_ssh_connectivity_evidence_schema(
    path: str | Path,
    report: LambdaSSHConnectivityEvidenceSchemaReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
