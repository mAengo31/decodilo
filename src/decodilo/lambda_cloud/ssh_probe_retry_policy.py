"""Retry policy for SSH probe failures."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.ssh_probe_diagnostic_artifact import (
    load_lambda_ssh_probe_diagnostic,
)

LambdaSSHProbeRetryPolicyStatus = Literal[
    "retry_blocked_pending_diagnostics",
    "future_retry_review_allowed",
]


class LambdaSSHProbeRetryPolicyReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    retry_policy_status: LambdaSSHProbeRetryPolicyStatus
    no_automatic_ssh_retry: bool = True
    unknown_exit_255_blocks_until_stderr_capture: bool = True
    required_before_future_retry: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_policy(self) -> LambdaSSHProbeRetryPolicyReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or not self.no_automatic_ssh_retry
            or not self.unknown_exit_255_blocks_until_stderr_capture
        ):
            raise ValueError("SSH retry policy cannot permit automatic retry")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_ssh_probe_retry_policy_from_path(
    probe_diagnostic: str | Path,
) -> LambdaSSHProbeRetryPolicyReport:
    diagnostic = load_lambda_ssh_probe_diagnostic(probe_diagnostic)
    required = [
        "username_policy_explicit",
        "host_key_policy_explicit",
        "identity_policy_explicit",
        "private_key_file_policy_explicit",
        "stderr_capture_policy_enabled",
        "operator_approval",
        "one_shot_arming_regenerated",
    ]
    blockers: list[str] = []
    warnings: list[str] = []
    if diagnostic.classification == "unknown_exit_255":
        blockers.append("unknown_exit_255_requires_redacted_stderr_capture")
    elif diagnostic.classification == "permission_denied_publickey":
        blockers.append("permission_denied_requires_username_identity_key_attachment_review")
    elif diagnostic.classification == "host_key_verification_failed":
        blockers.append("host_key_policy_must_be_fixed")
    else:
        warnings.append("future retry remains one-shot and operator-supervised only")
    return LambdaSSHProbeRetryPolicyReport(
        retry_policy_status=(
            "future_retry_review_allowed" if not blockers else "retry_blocked_pending_diagnostics"
        ),
        required_before_future_retry=required,
        blockers=blockers,
        warnings=warnings,
    )


def load_lambda_ssh_probe_retry_policy(path: str | Path) -> LambdaSSHProbeRetryPolicyReport:
    return LambdaSSHProbeRetryPolicyReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_ssh_probe_retry_policy(
    path: str | Path,
    report: LambdaSSHProbeRetryPolicyReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
