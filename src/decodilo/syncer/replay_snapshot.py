"""Snapshot-aware replay manifests and helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel, ConfigDict, Field

from decodilo.errors import ReplayMismatchError
from decodilo.storage.checksums import sha256_json
from decodilo.syncer.event_segments import EventSegmentReader
from decodilo.syncer.replay import ReplayState, replay_events

REPLAY_SNAPSHOT_SCHEMA_VERSION = "v1"


class ReplaySnapshot(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    global_version: int = Field(ge=0)
    logical_time: int = Field(ge=0)
    last_event_id: str
    last_segment_id: str | None = None
    global_state_checksum: str | None = None
    global_vector: list[float] | None = None
    idempotency_watermark: int = Field(default=0, ge=0)
    idempotency_store_checksum: str | None = None
    metrics_snapshot: dict[str, Any] = Field(default_factory=dict)
    committed_rounds: int = Field(ge=0)
    useful_tokens_accepted: int = Field(ge=0)
    artifact_refs: list[dict[str, Any]] = Field(default_factory=list)
    snapshot_hash: str
    schema_version: str = REPLAY_SNAPSHOT_SCHEMA_VERSION


class ReplaySnapshotManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    snapshot: ReplaySnapshot
    path: str


def _snapshot_hash_payload(data: dict[str, Any]) -> dict[str, Any]:
    payload = dict(data)
    payload.pop("snapshot_hash", None)
    return payload


def make_replay_snapshot(
    *,
    run_id: str,
    global_version: int,
    logical_time: int,
    last_event_id: str,
    committed_rounds: int,
    useful_tokens_accepted: int,
    global_vector: NDArray[np.float64] | list[float] | None = None,
    last_segment_id: str | None = None,
    metrics_snapshot: dict[str, Any] | None = None,
    artifact_refs: list[dict[str, Any]] | None = None,
    idempotency_watermark: int = 0,
    idempotency_store_checksum: str | None = None,
) -> ReplaySnapshot:
    vector_payload = None
    if global_vector is not None:
        vector_payload = np.asarray(global_vector, dtype=np.float64).astype(float).tolist()
    payload = {
        "run_id": run_id,
        "global_version": global_version,
        "logical_time": logical_time,
        "last_event_id": last_event_id,
        "last_segment_id": last_segment_id,
        "global_state_checksum": (
            sha256_json(vector_payload) if vector_payload is not None else None
        ),
        "global_vector": vector_payload,
        "idempotency_watermark": idempotency_watermark,
        "idempotency_store_checksum": idempotency_store_checksum,
        "metrics_snapshot": metrics_snapshot or {},
        "committed_rounds": committed_rounds,
        "useful_tokens_accepted": useful_tokens_accepted,
        "artifact_refs": artifact_refs or [],
        "schema_version": REPLAY_SNAPSHOT_SCHEMA_VERSION,
    }
    payload["snapshot_hash"] = sha256_json(_snapshot_hash_payload(payload))
    return ReplaySnapshot.model_validate(payload)


def validate_replay_snapshot(snapshot: ReplaySnapshot) -> None:
    if snapshot.schema_version != REPLAY_SNAPSHOT_SCHEMA_VERSION:
        raise ReplayMismatchError("unknown replay snapshot schema")
    expected = sha256_json(_snapshot_hash_payload(snapshot.model_dump(mode="json")))
    if expected != snapshot.snapshot_hash:
        raise ReplayMismatchError("replay snapshot_hash mismatch")
    if snapshot.global_vector is not None:
        checksum = sha256_json(snapshot.global_vector)
        if checksum != snapshot.global_state_checksum:
            raise ReplayMismatchError("replay snapshot global state checksum mismatch")


def write_replay_snapshot(path: str | Path, snapshot: ReplaySnapshot) -> None:
    validate_replay_snapshot(snapshot)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(
        json.dumps(snapshot.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    tmp.replace(target)


def load_replay_snapshot(path: str | Path) -> ReplaySnapshot:
    snapshot = ReplaySnapshot.model_validate_json(Path(path).read_text(encoding="utf-8"))
    validate_replay_snapshot(snapshot)
    return snapshot


def replay_from_snapshot_and_segments(
    *,
    snapshot_path: str | Path,
    segment_manifest_path: str | Path,
    artifact_workdir: str | Path | None = None,
) -> ReplayState:
    """Replay only events after a validated snapshot."""

    snapshot = load_replay_snapshot(snapshot_path)
    reader = EventSegmentReader(segment_manifest_path)
    events = [
        event
        for event in reader.iter_events()
        if event.logical_time > snapshot.logical_time
        and event.sequence > _event_sequence(snapshot.last_event_id)
    ]
    for event in events:
        if event.run_id != snapshot.run_id:
            raise ReplayMismatchError("tail event run_id differs from snapshot")
    resolved_artifact_workdir = (
        Path(artifact_workdir) if artifact_workdir else Path(segment_manifest_path).parent.parent
    )
    state = replay_events(
        events,
        artifact_workdir=resolved_artifact_workdir,
        initial_global_version=snapshot.global_version,
        initial_global_vector=(
            np.asarray(snapshot.global_vector, dtype=np.float64)
            if snapshot.global_vector is not None
            else None
        ),
        initial_useful_tokens=snapshot.useful_tokens_accepted,
    )
    if state.global_versions and min(state.global_versions) < snapshot.global_version:
        raise ReplayMismatchError("global_version regressed after snapshot")
    return state


def _event_sequence(event_id: str) -> int:
    try:
        return int(event_id.split(":")[-2])
    except (ValueError, IndexError) as exc:
        raise ReplayMismatchError("snapshot last_event_id is not deterministic") from exc
