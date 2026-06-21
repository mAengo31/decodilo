"""Contract model for future remote artifact backends."""

from __future__ import annotations

import json
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from decodilo.storage.remote_backend_requirements import RemoteBackendRequirementSet


class RemoteArtifactBackendCapabilities(BaseModel):
    model_config = ConfigDict(frozen=True)

    backend_name: str
    remote_backend_enabled: bool = False
    supports_range_read: bool = False
    supports_conditional_put: bool = False
    supports_strong_read_after_write: bool = False
    supports_atomic_manifest_commit: bool = False
    supports_object_versioning: bool = False
    supports_server_side_encryption: bool = False
    supports_client_side_encryption: bool = False
    supports_lifecycle_rules: bool = False
    supports_delete_transactions: bool = False
    supports_idempotent_put: bool = False
    supports_idempotent_delete: bool = False
    supports_integrity_metadata: bool = False
    supports_auth_scopes: bool = False
    supports_bandwidth_accounting: bool = False
    supports_cost_accounting: bool = False


class RemoteArtifactBackendOperation(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    enabled: bool
    notes: str = ""


class RemoteArtifactBackendContractReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    backend_name: str
    remote_backend_enabled: bool
    passed: bool
    missing_capabilities: list[str] = Field(default_factory=list)
    operations: list[RemoteArtifactBackendOperation] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


class RemoteArtifactBackendContract(Protocol):
    def remote_capabilities(self) -> RemoteArtifactBackendCapabilities: ...


def validate_remote_backend_contract(
    *,
    capabilities: RemoteArtifactBackendCapabilities,
    requirements: RemoteBackendRequirementSet,
) -> RemoteArtifactBackendContractReport:
    missing: list[str] = []
    checks = {
        "supports_range_read": True,
        "supports_conditional_put": requirements.required_conditional_put,
        "supports_strong_read_after_write": (
            requirements.required_read_after_write_consistency
        ),
        "supports_atomic_manifest_commit": requirements.required_atomic_manifest_commit,
        "supports_object_versioning": requirements.required_monotonic_manifest_visibility,
        "supports_server_side_encryption": requirements.required_encryption_at_rest,
        "supports_lifecycle_rules": requirements.required_lifecycle_delete,
        "supports_delete_transactions": requirements.required_transaction_log,
        "supports_idempotent_put": requirements.required_idempotent_put,
        "supports_idempotent_delete": requirements.required_idempotent_delete,
        "supports_integrity_metadata": requirements.required_content_hash_validation,
        "supports_auth_scopes": requirements.required_authentication,
        "supports_bandwidth_accounting": True,
        "supports_cost_accounting": True,
    }
    for field_name, required in checks.items():
        if required and not bool(getattr(capabilities, field_name)):
            missing.append(field_name)
    operations = [
        RemoteArtifactBackendOperation(name=name, enabled=False, notes="contract only")
        for name in [
            "put_artifact",
            "get_artifact",
            "get_range",
            "head_artifact",
            "list_artifacts",
            "delete_artifact",
            "conditional_put_manifest",
            "verify_artifact",
            "begin_delete_transaction",
            "commit_delete_transaction",
            "abort_delete_transaction",
            "lifecycle_mark",
            "lifecycle_list",
            "health_check",
        ]
    ]
    warnings = []
    if not capabilities.remote_backend_enabled:
        warnings.append("remote backend is disabled; report is contract-only")
    return RemoteArtifactBackendContractReport(
        backend_name=capabilities.backend_name,
        remote_backend_enabled=capabilities.remote_backend_enabled,
        passed=not missing and capabilities.remote_backend_enabled,
        missing_capabilities=missing,
        operations=operations,
        warnings=warnings,
    )

