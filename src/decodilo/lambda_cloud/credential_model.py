"""Symbolic Lambda API credential model.

No raw Lambda key values are accepted, read, or printed.
"""

from __future__ import annotations

import json
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.errors import LambdaCredentialError

_FORBIDDEN_FIELD_NAMES = {
    "api_key",
    "token",
    "secret",
    "password",
    "bearer",
    "authorization",
    "private_key",
}
_RAW_SECRET_PATTERN = re.compile(
    r"(lambda[_-]?[a-z0-9]{16,}|AKIA[0-9A-Z]{12,}|[A-Za-z0-9+/]{32,}={0,2})"
)


class LambdaAPIKeyRef(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    key_name: str
    owner: str | None = None
    purpose: str
    required_scope: Literal["read_only", "launch_control", "billing_read", "unknown"]
    created_by: str | None = None
    rotation_policy: str | None = None
    notes: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _reject_secret_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            lower_keys = {str(key).lower() for key in data}
            forbidden = lower_keys.intersection(_FORBIDDEN_FIELD_NAMES)
            if forbidden:
                raise LambdaCredentialError(
                    f"raw Lambda credential fields are forbidden: {sorted(forbidden)}"
                )
            for value in data.values():
                _reject_raw_secret_value(value)
        return data


class LambdaCredentialPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    policy_schema_version: int = 1
    api_key_refs: list[LambdaAPIKeyRef] = Field(default_factory=list)
    raw_secret_values_allowed: bool = False
    env_reads_allowed: bool = False
    reports_redact_suspicious_values: bool = True
    notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_policy(self) -> LambdaCredentialPolicy:
        if self.raw_secret_values_allowed:
            raise LambdaCredentialError("raw Lambda API keys are never allowed in M018")
        if self.env_reads_allowed:
            raise LambdaCredentialError("Lambda credential environment reads are disabled")
        return self


class LambdaCredentialAuditReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    passed: bool
    symbolic_ref_count: int
    raw_secret_detected: bool
    env_reads_allowed: bool
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def audit_lambda_credentials(policy: LambdaCredentialPolicy) -> LambdaCredentialAuditReport:
    errors: list[str] = []
    warnings: list[str] = []
    if policy.env_reads_allowed:
        errors.append("Lambda credential environment reads are disabled")
    if policy.raw_secret_values_allowed:
        errors.append("raw Lambda API keys are forbidden")
    if not policy.api_key_refs:
        warnings.append("no symbolic Lambda API key reference configured")
    return LambdaCredentialAuditReport(
        passed=not errors,
        symbolic_ref_count=len(policy.api_key_refs),
        raw_secret_detected=bool(errors),
        env_reads_allowed=policy.env_reads_allowed,
        warnings=warnings,
        errors=errors,
    )


def redact_suspicious_lambda_values(payload: Any) -> Any:
    if isinstance(payload, dict):
        redacted: dict[str, Any] = {}
        for key, value in payload.items():
            if str(key).lower() in _FORBIDDEN_FIELD_NAMES:
                redacted[key] = "<redacted>"
            else:
                redacted[key] = redact_suspicious_lambda_values(value)
        return redacted
    if isinstance(payload, list):
        return [redact_suspicious_lambda_values(item) for item in payload]
    if isinstance(payload, str) and _RAW_SECRET_PATTERN.search(payload):
        return "<redacted>"
    return payload


def _reject_raw_secret_value(value: Any) -> None:
    if isinstance(value, str) and _RAW_SECRET_PATTERN.search(value):
        raise LambdaCredentialError("raw-looking Lambda API key value is forbidden")
    if isinstance(value, dict):
        for nested_key, nested_value in value.items():
            if str(nested_key).lower() in _FORBIDDEN_FIELD_NAMES:
                raise LambdaCredentialError("raw Lambda credential fields are forbidden")
            _reject_raw_secret_value(nested_value)
    if isinstance(value, list):
        for item in value:
            _reject_raw_secret_value(item)
