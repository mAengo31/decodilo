"""Integrity policy model for future remote artifact backends."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class ManifestIntegrityPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    manifest_hash_required: bool = True
    conditional_manifest_put_required: bool = True
    monotonic_manifest_visibility_required: bool = True
    signed_manifest_required: bool = False


class ArtifactIntegrityPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    content_hash_required: bool = True
    chunk_hash_required: bool = True
    object_versioning_required: bool = True
    rollback_protection_required: bool = True


class IntegrityPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    policy_schema_version: int = 1
    manifest: ManifestIntegrityPolicy = Field(default_factory=ManifestIntegrityPolicy)
    artifact: ArtifactIntegrityPolicy = Field(default_factory=ArtifactIntegrityPolicy)


class IntegrityPolicyReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    passed: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    policy: IntegrityPolicy

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def evaluate_integrity_policy(policy: IntegrityPolicy) -> IntegrityPolicyReport:
    errors: list[str] = []
    warnings: list[str] = []
    if not policy.artifact.content_hash_required:
        errors.append("content hash validation is required")
    if not policy.artifact.chunk_hash_required:
        errors.append("chunk hash validation is required")
    if not policy.manifest.manifest_hash_required:
        errors.append("manifest hash validation is required")
    if not policy.manifest.conditional_manifest_put_required:
        errors.append("conditional manifest put is required")
    if not policy.artifact.object_versioning_required:
        warnings.append("object versioning is absent; stale artifact protection is weaker")
    if not policy.artifact.rollback_protection_required:
        errors.append("rollback protection is required")
    return IntegrityPolicyReport(
        passed=not errors,
        errors=errors,
        warnings=warnings,
        policy=policy,
    )


def load_integrity_policy(path: str | Path) -> IntegrityPolicy:
    return IntegrityPolicy.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_integrity_policy_report(path: str | Path, report: IntegrityPolicyReport) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
