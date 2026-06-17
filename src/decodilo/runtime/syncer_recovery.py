"""Syncer checkpoint recovery helpers."""

from __future__ import annotations

from decodilo.errors import InvariantViolation
from decodilo.runtime.syncer_checkpoint import SyncerCheckpoint


def require_checkpoint_for_run(checkpoint: SyncerCheckpoint, *, run_id: str) -> None:
    if checkpoint.run_id != run_id:
        raise InvariantViolation(
            f"syncer checkpoint run_id mismatch: {checkpoint.run_id!r} != {run_id!r}"
        )
    if checkpoint.global_version < 0:
        raise InvariantViolation("syncer checkpoint global_version must be non-negative")
