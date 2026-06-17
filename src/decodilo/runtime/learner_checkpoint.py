"""Atomic learner checkpoint persistence for local worker restarts."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from decodilo.errors import InvariantViolation
from decodilo.storage.artifact_reader import load_and_read_binary_artifact
from decodilo.storage.artifact_writer import write_binary_artifact
from decodilo.storage.chunk_store import ChunkStore
from decodilo.storage.errors import StorageError
from decodilo.storage.manifest import StorageArtifactManifest

LEARNER_CHECKPOINT_SCHEMA_VERSION = "v1"


class LearnerCheckpoint(BaseModel):
    model_config = ConfigDict(frozen=True)

    schema_version: str = LEARNER_CHECKPOINT_SCHEMA_VERSION
    run_id: str
    learner_id: str
    local_step: int = Field(ge=0)
    tokens_processed: int = Field(ge=0)
    tokens_since_last_sync: int = Field(ge=0)
    last_global_version_seen: int = Field(ge=0)
    last_applied_global_version: int = Field(ge=0)
    learner_state_version: int = Field(ge=0)
    throughput_tokens_per_step: int = Field(ge=0)
    parameter_vector: list[float]
    trainer_type: str = "numpy_convex"
    trainer_payload: dict[str, Any] = Field(default_factory=dict)
    written_logical_time: int = Field(ge=0)
    checksum: str


def _payload_for_checksum(data: dict) -> dict:
    copy = dict(data)
    copy.pop("checksum", None)
    return copy


def checkpoint_checksum(data: dict) -> str:
    encoded = json.dumps(
        _payload_for_checksum(data),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def make_checkpoint(
    *,
    run_id: str,
    learner_id: str,
    local_step: int,
    tokens_processed: int,
    tokens_since_last_sync: int,
    last_global_version_seen: int,
    last_applied_global_version: int,
    throughput_tokens_per_step: int,
    parameter_vector: list[float],
    trainer_type: str = "numpy_convex",
    trainer_payload: dict[str, Any] | None = None,
    written_logical_time: int,
) -> LearnerCheckpoint:
    payload = {
        "schema_version": LEARNER_CHECKPOINT_SCHEMA_VERSION,
        "run_id": run_id,
        "learner_id": learner_id,
        "local_step": local_step,
        "tokens_processed": tokens_processed,
        "tokens_since_last_sync": tokens_since_last_sync,
        "last_global_version_seen": last_global_version_seen,
        "last_applied_global_version": last_applied_global_version,
        "learner_state_version": 1,
        "throughput_tokens_per_step": throughput_tokens_per_step,
        "parameter_vector": parameter_vector,
        "trainer_type": trainer_type,
        "trainer_payload": trainer_payload or {},
        "written_logical_time": written_logical_time,
    }
    payload["checksum"] = checkpoint_checksum(payload)
    return LearnerCheckpoint.model_validate(payload)


def write_checkpoint_atomic(path: str | Path, checkpoint: LearnerCheckpoint) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(
        json.dumps(checkpoint.model_dump(mode="json"), sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(tmp, target)


def load_checkpoint(path: str | Path) -> LearnerCheckpoint:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        checkpoint = LearnerCheckpoint.model_validate(data)
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        raise InvariantViolation(f"invalid learner checkpoint: {exc}") from exc
    if checkpoint.schema_version != LEARNER_CHECKPOINT_SCHEMA_VERSION:
        raise InvariantViolation(f"unknown learner checkpoint schema {checkpoint.schema_version!r}")
    if checkpoint_checksum(checkpoint.model_dump(mode="json")) != checkpoint.checksum:
        raise InvariantViolation("learner checkpoint checksum mismatch")
    return checkpoint


def write_chunked_learner_checkpoint(
    *,
    manifest_path: str | Path,
    chunk_store_dir: str | Path,
    checkpoint: LearnerCheckpoint,
    chunk_size_bytes: int = 1024 * 1024,
) -> StorageArtifactManifest:
    store = ChunkStore(chunk_store_dir)
    payload = (
        json.dumps(checkpoint.model_dump(mode="json"), sort_keys=True) + "\n"
    ).encode("utf-8")
    return write_binary_artifact(
        store=store,
        data=payload,
        artifact_id=f"{checkpoint.run_id}:{checkpoint.learner_id}:learner_checkpoint",
        artifact_type="learner_checkpoint",
        run_id=checkpoint.run_id,
        chunk_size_bytes=chunk_size_bytes,
        metadata={
            "checkpoint_schema_version": checkpoint.schema_version,
            "component_type": "learner",
            "component_id": checkpoint.learner_id,
            "global_version": checkpoint.last_global_version_seen,
            "trainer_state_ref": "embedded_checkpoint_payload",
        },
        manifest_path=manifest_path,
    )


def load_chunked_learner_checkpoint(
    *,
    manifest_path: str | Path,
    chunk_store_dir: str | Path,
) -> LearnerCheckpoint:
    store = ChunkStore(chunk_store_dir)
    try:
        data = load_and_read_binary_artifact(store=store, manifest_path=manifest_path)
    except StorageError as exc:
        raise InvariantViolation(f"invalid chunked learner checkpoint: {exc}") from exc
    try:
        checkpoint = LearnerCheckpoint.model_validate_json(data.decode("utf-8"))
    except (UnicodeDecodeError, ValidationError) as exc:
        raise InvariantViolation(f"invalid chunked learner checkpoint: {exc}") from exc
    if checkpoint_checksum(checkpoint.model_dump(mode="json")) != checkpoint.checksum:
        raise InvariantViolation("learner checkpoint checksum mismatch")
    return checkpoint
