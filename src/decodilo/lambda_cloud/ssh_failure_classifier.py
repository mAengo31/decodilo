"""Classify redacted SSH probe failures."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

LambdaSSHFailureClassification = Literal[
    "tcp_timeout",
    "tcp_refused",
    "host_key_verification_failed",
    "permission_denied_publickey",
    "wrong_username_likely",
    "private_key_permissions_too_open",
    "identity_file_not_found",
    "unsupported_key_algorithm",
    "too_many_authentication_failures",
    "no_matching_host_key_type",
    "no_matching_pubkey_algorithm",
    "auth_failed_unknown",
    "ssh_protocol_error",
    "client_invocation_error",
    "unknown_exit_255",
]


class LambdaSSHFailureClassifierReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    classification: LambdaSSHFailureClassification
    exit_code: int | None = None
    tcp_readiness_succeeded: bool | None = None
    stderr_present: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> LambdaSSHFailureClassifierReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("SSH failure classifier cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def classify_ssh_failure(
    *,
    exit_code: int | None,
    stderr_redacted: str | None,
    tcp_readiness_succeeded: bool | None = None,
) -> LambdaSSHFailureClassifierReport:
    text = (stderr_redacted or "").lower()
    classification: LambdaSSHFailureClassification
    if "operation timed out" in text or "connection timed out" in text:
        classification = "tcp_timeout"
    elif "connection refused" in text:
        classification = "tcp_refused"
    elif "host key verification failed" in text:
        classification = "host_key_verification_failed"
    elif "unprotected private key file" in text:
        classification = "private_key_permissions_too_open"
    elif "identity file" in text and ("not accessible" in text or "no such file" in text):
        classification = "identity_file_not_found"
    elif "too many authentication failures" in text:
        classification = "too_many_authentication_failures"
    elif "no matching host key type" in text:
        classification = "no_matching_host_key_type"
    elif "no matching pubkey" in text or "no mutual signature algorithm" in text:
        classification = "no_matching_pubkey_algorithm"
    elif "bad permissions" in text or "invalid format" in text:
        classification = "unsupported_key_algorithm"
    elif "protocol" in text and "error" in text:
        classification = "ssh_protocol_error"
    elif "permission denied (publickey)" in text or "permission denied" in text:
        classification = (
            "permission_denied_publickey"
            if tcp_readiness_succeeded
            else "auth_failed_unknown"
        )
    elif text.strip():
        classification = (
            "client_invocation_error"
            if exit_code not in {255, None}
            else "auth_failed_unknown"
        )
    elif exit_code == 255:
        classification = "unknown_exit_255"
    else:
        classification = "auth_failed_unknown"
    warnings: list[str] = []
    if classification == "permission_denied_publickey":
        warnings.append("review username, identity selection, and provider key attachment")
    if classification == "unknown_exit_255":
        warnings.append("enable bounded redacted stderr capture before another live retry")
    return LambdaSSHFailureClassifierReport(
        classification=classification,
        exit_code=exit_code,
        tcp_readiness_succeeded=tcp_readiness_succeeded,
        stderr_present=bool(stderr_redacted),
        warnings=warnings,
    )


def load_lambda_ssh_failure_classifier(
    path: str | Path,
) -> LambdaSSHFailureClassifierReport:
    return LambdaSSHFailureClassifierReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_ssh_failure_classifier(
    path: str | Path,
    report: LambdaSSHFailureClassifierReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
