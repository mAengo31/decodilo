"""Idempotency policy model for future remote artifact backends."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class RemoteBackendIdempotencyPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    policy_schema_version: int = 1
    idempotent_put_required: bool = True
    idempotent_delete_required: bool = True
    conditional_manifest_commit_required: bool = True
    retry_token_model: str = "symbolic_retry_key"
    duplicate_suppression_window_seconds: int = Field(default=86_400, ge=0)
    transaction_id_model: str = "content_hash_plus_logical_transaction"


class RemoteBackendIdempotencyReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    passed: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    policy: RemoteBackendIdempotencyPolicy

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def evaluate_remote_backend_idempotency(
    policy: RemoteBackendIdempotencyPolicy,
) -> RemoteBackendIdempotencyReport:
    errors: list[str] = []
    warnings: list[str] = []
    if not policy.idempotent_put_required:
        errors.append("idempotent put is required")
    if not policy.idempotent_delete_required:
        errors.append("idempotent delete is required")
    if not policy.conditional_manifest_commit_required:
        errors.append("conditional manifest commit is required")
    if not policy.retry_token_model:
        errors.append("retry token model is required")
    if policy.duplicate_suppression_window_seconds < 3600:
        warnings.append("duplicate suppression window is short for long-running training")
    if not policy.transaction_id_model:
        errors.append("transaction id model is required")
    return RemoteBackendIdempotencyReport(
        passed=not errors,
        errors=errors,
        warnings=warnings,
        policy=policy,
    )


def load_remote_backend_idempotency_policy(path: str | Path) -> RemoteBackendIdempotencyPolicy:
    return RemoteBackendIdempotencyPolicy.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_remote_backend_idempotency_report(
    path: str | Path,
    report: RemoteBackendIdempotencyReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
