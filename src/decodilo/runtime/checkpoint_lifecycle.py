"""Checkpoint retention planning for local runs."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class CheckpointLifecyclePolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    keep_latest_n_syncer_checkpoints: int = Field(default=1, ge=1)
    keep_latest_n_learner_checkpoints: int = Field(default=1, ge=1)
    checkpoint_every_n_rounds: int = Field(default=1, ge=1)
    snapshot_every_n_checkpoints: int = Field(default=1, ge=1)


class CheckpointLifecycleReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    checkpoints_written: int
    checkpoints_retained: int
    checkpoints_gc_eligible: int
    latest_recovery_checkpoint: str | None
    snapshot_count: int
    retained_paths: list[str]
    gc_eligible_paths: list[str]


def plan_checkpoint_lifecycle(
    *,
    syncer_checkpoints: list[str | Path],
    learner_checkpoints: list[str | Path] | None = None,
    policy: CheckpointLifecyclePolicy | None = None,
) -> CheckpointLifecycleReport:
    """Return retention decisions without deleting anything."""

    policy = policy or CheckpointLifecyclePolicy()
    syncer_paths = sorted((Path(path) for path in syncer_checkpoints), key=lambda p: str(p))
    learner_paths = sorted((Path(path) for path in learner_checkpoints or []), key=lambda p: str(p))
    retained = set(syncer_paths[-policy.keep_latest_n_syncer_checkpoints :])
    retained.update(learner_paths[-policy.keep_latest_n_learner_checkpoints :])
    all_paths = [*syncer_paths, *learner_paths]
    eligible = [path for path in all_paths if path not in retained]
    latest = str(syncer_paths[-1]) if syncer_paths else None
    return CheckpointLifecycleReport(
        checkpoints_written=len(all_paths),
        checkpoints_retained=len(retained),
        checkpoints_gc_eligible=len(eligible),
        latest_recovery_checkpoint=latest,
        snapshot_count=max(0, len(syncer_paths) // policy.snapshot_every_n_checkpoints),
        retained_paths=[str(path) for path in sorted(retained, key=lambda p: str(p))],
        gc_eligible_paths=[str(path) for path in eligible],
    )

