"""Threat model and security checklist for future remote artifact backends."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator

from decodilo.storage.remote_backend_requirements import RemoteBackendRequirementSet


class RemoteBackendThreatModel(BaseModel):
    model_config = ConfigDict(frozen=True)

    threats: list[str] = Field(
        default_factory=lambda: [
            "artifact corruption",
            "stale manifest read",
            "malicious worker submitting bad artifact refs",
            "path or URI injection",
            "credential leakage",
            "unauthorized artifact reads",
            "unauthorized artifact deletes",
            "replay using wrong artifact version",
            "partial writes",
            "rollback attacks",
            "poisoned global updates",
            "data exfiltration through artifact access",
            "deletion of live artifacts",
        ]
    )


class RemoteBackendSecurityChecklist(BaseModel):
    model_config = ConfigDict(frozen=True)

    auth_required: bool = True
    scoped_credentials_required: bool = True
    credential_names: list[str] = Field(default_factory=list)
    no_credentials_in_logs: bool = True
    encryption_in_transit: bool = True
    encryption_at_rest: bool = True
    client_side_hash_validation: bool = True
    signed_manifest_optional: bool = False
    conditional_manifest_put: bool = True
    object_versioning: bool = True
    delete_transaction_log: bool = True
    lifecycle_policy: bool = True
    audit_log: bool = True
    worker_artifact_scope: bool = True
    syncer_artifact_scope: bool = True
    preflight_required: bool = True
    teardown_required: bool = True

    @field_validator("credential_names")
    @classmethod
    def _reject_secret_values(cls, values: list[str]) -> list[str]:
        for value in values:
            lowered = value.lower()
            if "=" in value or "secret" in lowered and len(value) > 64:
                raise ValueError("credential_names must contain redacted names, not values")
        return values


class RemoteBackendSecurityReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    passed: bool
    threat_model: RemoteBackendThreatModel
    checklist: RemoteBackendSecurityChecklist
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def evaluate_remote_backend_security(
    *,
    requirements: RemoteBackendRequirementSet,
    checklist: RemoteBackendSecurityChecklist | None = None,
) -> RemoteBackendSecurityReport:
    active = checklist or RemoteBackendSecurityChecklist()
    errors: list[str] = []
    warnings: list[str] = []
    if requirements.required_authentication and not active.auth_required:
        errors.append("authentication is required")
    if requirements.required_authentication and not active.scoped_credentials_required:
        errors.append("scoped credentials are required")
    if requirements.required_encryption_in_transit and not active.encryption_in_transit:
        errors.append("encryption in transit is required")
    if requirements.required_encryption_at_rest and not active.encryption_at_rest:
        errors.append("encryption at rest is required")
    if requirements.required_content_hash_validation and not active.client_side_hash_validation:
        errors.append("client-side content hash validation is required")
    if requirements.required_conditional_put and not active.conditional_manifest_put:
        errors.append("conditional manifest put is required")
    if not active.object_versioning:
        warnings.append("object versioning is absent; rollback protection is weaker")
    if not active.audit_log:
        warnings.append("audit log is absent; incident reconstruction is weaker")
    return RemoteBackendSecurityReport(
        passed=not errors,
        threat_model=RemoteBackendThreatModel(),
        checklist=active,
        errors=errors,
        warnings=warnings,
    )


def write_remote_backend_security_report(
    path: str | Path,
    report: RemoteBackendSecurityReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")


def load_remote_backend_security_report(path: str | Path) -> RemoteBackendSecurityReport:
    return RemoteBackendSecurityReport.model_validate_json(Path(path).read_text(encoding="utf-8"))

