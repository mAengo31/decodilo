"""Lifecycle requirements for future remote artifact backends."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from decodilo.storage.remote_backend_requirements import RemoteBackendRequirementSet


class RemoteBackendRetentionRule(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    keep_latest_count: int = Field(ge=0)
    protected: bool = True


class RemoteBackendLifecyclePlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    dry_run_gc_required: bool = True
    transaction_log_required: bool = True
    protected_live_artifacts_required: bool = True
    retention_policy_required: bool = True
    lifecycle_cleanup_window_hours: float = Field(default=24.0, gt=0)
    auditability_required: bool = True
    retention_rules: list[RemoteBackendRetentionRule] = Field(
        default_factory=lambda: [
            RemoteBackendRetentionRule(name="latest_checkpoint", keep_latest_count=1),
            RemoteBackendRetentionRule(name="latest_global_state", keep_latest_count=1),
        ]
    )


class RemoteBackendCleanupPlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    dry_run_only: bool = True
    candidate_delete_count: int = Field(default=0, ge=0)
    requires_transaction_log: bool = True


class RemoteBackendLifecycleValidationReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    passed: bool
    plan: RemoteBackendLifecyclePlan
    cleanup_plan: RemoteBackendCleanupPlan
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def validate_remote_backend_lifecycle(
    *,
    requirements: RemoteBackendRequirementSet,
    plan: RemoteBackendLifecyclePlan | None = None,
) -> RemoteBackendLifecycleValidationReport:
    active = plan or RemoteBackendLifecyclePlan()
    errors: list[str] = []
    warnings: list[str] = []
    if requirements.required_transaction_log and not active.transaction_log_required:
        errors.append("delete transaction log is required")
    if requirements.required_retention_policy and not active.retention_policy_required:
        errors.append("retention policy is required")
    if requirements.required_lifecycle_delete and not active.dry_run_gc_required:
        errors.append("dry-run GC equivalent is required")
    if not active.protected_live_artifacts_required:
        errors.append("live artifacts must be protected")
    if active.lifecycle_cleanup_window_hours > 24 * 7:
        warnings.append("provider lifecycle delay exceeds typical recovery retention windows")
    return RemoteBackendLifecycleValidationReport(
        passed=not errors,
        plan=active,
        cleanup_plan=RemoteBackendCleanupPlan(),
        errors=errors,
        warnings=warnings,
    )


def write_remote_backend_lifecycle_report(
    path: str | Path,
    report: RemoteBackendLifecycleValidationReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")

