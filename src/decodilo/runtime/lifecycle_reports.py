"""Reports for lifecycle stress and audit commands."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class LifecycleStressReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    cycles_completed: int
    checkpoints_written: int
    compactions_performed: int
    snapshots_written: int
    gc_plans_written: int
    syncer_restarts: int
    genesis_replay_passed: bool
    snapshot_replay_passed: bool
    artifact_audit_passed: bool
    run_validate_passed: bool
    max_event_segment_count: int
    idempotency_records_before_after: list[dict[str, int]] = Field(default_factory=list)
    gc_reclaimable_bytes: int = 0
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

