"""Evidence schema for a future supervised Lambda remote bootstrap."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

BOOTSTRAP_EVIDENCE_FIELDS = (
    "launch_report",
    "owned_instance_id_redacted",
    "selected_instance_type",
    "region",
    "running_verification",
    "remote_access_mode",
    "ssh_connectivity_result",
    "command_outputs_redacted_bounded",
    "command_duration_seconds",
    "exit_code",
    "no_package_install_proof",
    "no_training_proof",
    "termination_report",
    "termination_verification",
    "spend_audit",
    "final_discovery",
    "secret_scan",
    "metadata_bootstrap_success_record",
    "metadata_bootstrap_reconciliation",
    "metadata_bootstrap_closeout",
    "no_remote_execution_attestation",
)


class LambdaBootstrapEvidenceSchemaReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    evidence_schema_status: str = "schema_valid"
    required_evidence_fields: list[str] = Field(default_factory=list)
    command_output_max_bytes: int = 4096
    command_timeout_seconds: int = 30
    secret_redaction_required: bool = True
    raw_secret_storage_allowed: bool = False
    schema_valid: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_schema_bounds(self) -> LambdaBootstrapEvidenceSchemaReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.raw_secret_storage_allowed
            or not self.secret_redaction_required
            or self.command_output_max_bytes <= 0
            or self.command_output_max_bytes > 16_384
        ):
            raise ValueError("bootstrap evidence schema has unsafe bounds")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_bootstrap_evidence_schema() -> LambdaBootstrapEvidenceSchemaReport:
    return LambdaBootstrapEvidenceSchemaReport(
        required_evidence_fields=list(BOOTSTRAP_EVIDENCE_FIELDS),
        warnings=[
            "M050 only defines future evidence requirements",
            "remote command output must be bounded and redacted if M051 approves commands",
            "M052 metadata bootstrap closeout evidence must remain offline/no-launch",
        ],
    )


def load_lambda_bootstrap_evidence_schema(
    path: str | Path,
) -> LambdaBootstrapEvidenceSchemaReport:
    return LambdaBootstrapEvidenceSchemaReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_bootstrap_evidence_schema(
    path: str | Path,
    report: LambdaBootstrapEvidenceSchemaReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
