"""Credential planning models for future remote artifact backends.

The models in this module intentionally accept symbolic references only. They
do not read process environment, credentials files, cloud SDKs, or secret
stores.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_FORBIDDEN_SECRET_FIELDS = {
    "secret_value",
    "access_key",
    "secret_key",
    "token",
    "password",
    "private_key",
}
_SUSPICIOUS_VALUE = re.compile(
    r"(AKIA[0-9A-Z]{12,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|[A-Za-z0-9_=-]{80,})"
)


class SecretRef(BaseModel):
    """Symbolic reference to a future secret, never the secret itself."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    provider: str
    purpose: str
    required: bool = True
    rotation_policy: str | None = None
    notes: list[str] = Field(default_factory=list)

    @field_validator("name", "provider", "purpose", "rotation_policy")
    @classmethod
    def _reject_secret_like_values(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if "=" in value or _SUSPICIOUS_VALUE.search(value):
            raise ValueError("SecretRef fields must be symbolic metadata, not raw secret values")
        return value

    @field_validator("notes")
    @classmethod
    def _reject_secret_like_notes(cls, values: list[str]) -> list[str]:
        for value in values:
            if "=" in value or _SUSPICIOUS_VALUE.search(value):
                raise ValueError("SecretRef notes must not contain raw secret values")
        return values


class CredentialRequirement(BaseModel):
    model_config = ConfigDict(frozen=True)

    requirement_id: str
    secret_ref: SecretRef
    required_for_operations: list[str] = Field(default_factory=list)
    least_privilege_required: bool = True
    rotation_required: bool = True


class CredentialHandlingPolicy(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    policy_schema_version: int = 1
    credential_requirements: list[CredentialRequirement] = Field(default_factory=list)
    raw_secrets_allowed: bool = False
    read_environment_variables: bool = False
    print_secrets_in_reports: bool = False
    no_credentials_in_logs: bool = True

    @model_validator(mode="before")
    @classmethod
    def _reject_forbidden_raw_fields(cls, data: object) -> object:
        if isinstance(data, dict):
            found = sorted(set(data) & _FORBIDDEN_SECRET_FIELDS)
            if found:
                raise ValueError(f"raw secret fields are not accepted: {found}")
        return data


class CredentialAuditReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    passed: bool
    credential_count: int
    symbolic_secret_refs: list[dict]
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    redacted: bool = True

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def audit_credential_policy(policy: CredentialHandlingPolicy) -> CredentialAuditReport:
    errors: list[str] = []
    warnings: list[str] = []
    if policy.raw_secrets_allowed:
        errors.append("raw secrets must not be accepted")
    if policy.read_environment_variables:
        errors.append("credential policy must not read environment variables")
    if policy.print_secrets_in_reports:
        errors.append("credential policy must not print secrets in reports")
    if not policy.no_credentials_in_logs:
        errors.append("credentials must not appear in logs")
    for requirement in policy.credential_requirements:
        if requirement.secret_ref.required and not requirement.secret_ref.rotation_policy:
            warnings.append(f"credential {requirement.requirement_id} has no rotation policy")
    refs = [
        {
            "name": item.secret_ref.name,
            "provider": item.secret_ref.provider,
            "purpose": item.secret_ref.purpose,
            "required": item.secret_ref.required,
        }
        for item in policy.credential_requirements
    ]
    return CredentialAuditReport(
        passed=not errors,
        credential_count=len(policy.credential_requirements),
        symbolic_secret_refs=refs,
        errors=errors,
        warnings=warnings,
    )


def load_credential_handling_policy(path: str | Path) -> CredentialHandlingPolicy:
    return CredentialHandlingPolicy.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_credential_audit_report(path: str | Path, report: CredentialAuditReport) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
