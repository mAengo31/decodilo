"""Replay and restore requirements for future remote artifact backends."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class RemoteBackendReplayRestorePolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    policy_schema_version: int = 1
    recovery_manifest_availability_required: bool = True
    checkpoint_artifact_availability_required: bool = True
    replay_snapshot_artifact_availability_required: bool = True
    event_segment_availability_required: bool = True
    object_version_compatibility_required: bool = True
    stale_object_protection_required: bool = True
    range_read_hash_validation_required: bool = True


class RemoteBackendReplayRestoreReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    passed: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    policy: RemoteBackendReplayRestorePolicy

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def evaluate_remote_backend_replay_restore(
    policy: RemoteBackendReplayRestorePolicy,
) -> RemoteBackendReplayRestoreReport:
    errors: list[str] = []
    required = {
        "recovery_manifest_availability_required": policy.recovery_manifest_availability_required,
        "checkpoint_artifact_availability_required": (
            policy.checkpoint_artifact_availability_required
        ),
        "replay_snapshot_artifact_availability_required": (
            policy.replay_snapshot_artifact_availability_required
        ),
        "event_segment_availability_required": policy.event_segment_availability_required,
        "object_version_compatibility_required": policy.object_version_compatibility_required,
        "stale_object_protection_required": policy.stale_object_protection_required,
        "range_read_hash_validation_required": policy.range_read_hash_validation_required,
    }
    for field_name, enabled in required.items():
        if not enabled:
            errors.append(f"{field_name} must be enabled")
    return RemoteBackendReplayRestoreReport(
        passed=not errors,
        errors=errors,
        policy=policy,
    )


def load_remote_backend_replay_restore_policy(path: str | Path) -> RemoteBackendReplayRestorePolicy:
    return RemoteBackendReplayRestorePolicy.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_remote_backend_replay_restore_report(
    path: str | Path,
    report: RemoteBackendReplayRestoreReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
