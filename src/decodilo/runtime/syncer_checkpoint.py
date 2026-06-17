"""Atomic syncer checkpoint persistence."""

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

SYNCER_CHECKPOINT_SCHEMA_VERSION = "v1"


class SyncerCheckpoint(BaseModel):
    model_config = ConfigDict(frozen=True)

    checkpoint_schema_version: str = SYNCER_CHECKPOINT_SCHEMA_VERSION
    run_id: str
    global_version: int = Field(ge=0)
    global_vector: list[float]
    outer_optimizer_state: dict[str, Any] = Field(default_factory=dict)
    fragment_store_state: dict[str, Any] = Field(default_factory=dict)
    learner_registry_state: dict[str, Any] = Field(default_factory=dict)
    idempotency_table: dict[str, dict[str, Any]] = Field(default_factory=dict)
    committed_round_state: dict[str, Any] = Field(default_factory=dict)
    pending_round_state: dict[str, Any] = Field(default_factory=dict)
    metrics_snapshot: dict[str, Any] = Field(default_factory=dict)
    event_log_offset: int = Field(ge=0)
    last_event_id: str | None = None
    checksum: str
    written_logical_time: int = Field(ge=0)


def _payload_for_checksum(data: dict[str, Any]) -> dict[str, Any]:
    payload = dict(data)
    payload.pop("checksum", None)
    return payload


def syncer_checkpoint_checksum(data: dict[str, Any]) -> str:
    encoded = json.dumps(
        _payload_for_checksum(data),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def make_syncer_checkpoint(
    *,
    run_id: str,
    global_version: int,
    global_vector: list[float],
    outer_optimizer_state: dict[str, Any],
    fragment_store_state: dict[str, Any],
    learner_registry_state: dict[str, Any],
    idempotency_table: dict[str, dict[str, Any]],
    committed_round_state: dict[str, Any],
    pending_round_state: dict[str, Any],
    metrics_snapshot: dict[str, Any],
    event_log_offset: int,
    last_event_id: str | None,
    written_logical_time: int,
) -> SyncerCheckpoint:
    payload = {
        "checkpoint_schema_version": SYNCER_CHECKPOINT_SCHEMA_VERSION,
        "run_id": run_id,
        "global_version": global_version,
        "global_vector": global_vector,
        "outer_optimizer_state": outer_optimizer_state,
        "fragment_store_state": fragment_store_state,
        "learner_registry_state": learner_registry_state,
        "idempotency_table": idempotency_table,
        "committed_round_state": committed_round_state,
        "pending_round_state": pending_round_state,
        "metrics_snapshot": metrics_snapshot,
        "event_log_offset": event_log_offset,
        "last_event_id": last_event_id,
        "written_logical_time": written_logical_time,
    }
    payload["checksum"] = syncer_checkpoint_checksum(payload)
    return SyncerCheckpoint.model_validate(payload)


def write_syncer_checkpoint_atomic(path: str | Path, checkpoint: SyncerCheckpoint) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(
        json.dumps(checkpoint.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(tmp, target)


def load_syncer_checkpoint(path: str | Path) -> SyncerCheckpoint:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        checkpoint = SyncerCheckpoint.model_validate(data)
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        raise InvariantViolation(f"invalid syncer checkpoint: {exc}") from exc
    if checkpoint.checkpoint_schema_version != SYNCER_CHECKPOINT_SCHEMA_VERSION:
        raise InvariantViolation(
            f"unknown syncer checkpoint schema {checkpoint.checkpoint_schema_version!r}"
        )
    if syncer_checkpoint_checksum(checkpoint.model_dump(mode="json")) != checkpoint.checksum:
        raise InvariantViolation("syncer checkpoint checksum mismatch")
    return checkpoint


def write_chunked_syncer_checkpoint(
    *,
    manifest_path: str | Path,
    chunk_store_dir: str | Path,
    checkpoint: SyncerCheckpoint,
    chunk_size_bytes: int = 1024 * 1024,
) -> StorageArtifactManifest:
    store = ChunkStore(chunk_store_dir)
    payload = (
        json.dumps(checkpoint.model_dump(mode="json"), sort_keys=True) + "\n"
    ).encode("utf-8")
    return write_binary_artifact(
        store=store,
        data=payload,
        artifact_id=f"{checkpoint.run_id}:syncer_checkpoint:{checkpoint.global_version}",
        artifact_type="syncer_checkpoint",
        run_id=checkpoint.run_id,
        chunk_size_bytes=chunk_size_bytes,
        metadata={
            "checkpoint_schema_version": checkpoint.checkpoint_schema_version,
            "component_type": "syncer",
            "component_id": "syncer",
            "global_version": checkpoint.global_version,
            "syncer_state_ref": "embedded_checkpoint_payload",
        },
        manifest_path=manifest_path,
    )


def load_chunked_syncer_checkpoint(
    *,
    manifest_path: str | Path,
    chunk_store_dir: str | Path,
) -> SyncerCheckpoint:
    store = ChunkStore(chunk_store_dir)
    try:
        data = load_and_read_binary_artifact(store=store, manifest_path=manifest_path)
    except StorageError as exc:
        raise InvariantViolation(f"invalid chunked syncer checkpoint: {exc}") from exc
    try:
        checkpoint = SyncerCheckpoint.model_validate_json(data.decode("utf-8"))
    except (UnicodeDecodeError, ValidationError) as exc:
        raise InvariantViolation(f"invalid chunked syncer checkpoint: {exc}") from exc
    if syncer_checkpoint_checksum(checkpoint.model_dump(mode="json")) != checkpoint.checksum:
        raise InvariantViolation("syncer checkpoint checksum mismatch")
    return checkpoint
