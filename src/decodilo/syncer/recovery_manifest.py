"""Recovery manifest for syncer restart prerequisites."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from decodilo.errors import InvariantViolation
from decodilo.storage.checksums import sha256_json

RECOVERY_MANIFEST_SCHEMA_VERSION = "v1"
RecoverySource = Literal["inline", "chunked", "dual"]


class RecoveryManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    manifest_id: str
    schema_version: str = RECOVERY_MANIFEST_SCHEMA_VERSION
    created_logical_time: int = Field(ge=0)
    global_version: int | None = Field(default=None, ge=0)
    checkpoint_ref: dict[str, Any]
    checkpoint_storage_mode: str
    recovery_source: RecoverySource
    replay_snapshot_ref: dict[str, Any] | None = None
    event_segment_refs: list[dict[str, Any]] = Field(default_factory=list)
    global_state_refs: list[dict[str, Any]] = Field(default_factory=list)
    idempotency_store_ref: dict[str, Any] | None = None
    artifact_manifest_ref: dict[str, Any] | None = None
    required_artifact_hashes: dict[str, str] = Field(default_factory=dict)
    compaction_watermarks: dict[str, int] = Field(default_factory=dict)
    previous_recovery_manifest_hash: str | None = None
    manifest_hash: str

    def stable_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))


def _hash_payload(data: dict[str, Any]) -> dict[str, Any]:
    payload = dict(data)
    payload.pop("manifest_hash", None)
    return payload


def make_recovery_manifest(
    *,
    run_id: str,
    manifest_id: str,
    created_logical_time: int,
    checkpoint_ref: dict[str, Any],
    checkpoint_storage_mode: str,
    recovery_source: RecoverySource,
    global_version: int | None = None,
    replay_snapshot_ref: dict[str, Any] | None = None,
    event_segment_refs: list[dict[str, Any]] | None = None,
    global_state_refs: list[dict[str, Any]] | None = None,
    idempotency_store_ref: dict[str, Any] | None = None,
    artifact_manifest_ref: dict[str, Any] | None = None,
    required_artifact_hashes: dict[str, str] | None = None,
    compaction_watermarks: dict[str, int] | None = None,
    previous_recovery_manifest_hash: str | None = None,
) -> RecoveryManifest:
    payload = {
        "run_id": run_id,
        "manifest_id": manifest_id,
        "schema_version": RECOVERY_MANIFEST_SCHEMA_VERSION,
        "created_logical_time": created_logical_time,
        "global_version": global_version,
        "checkpoint_ref": checkpoint_ref,
        "checkpoint_storage_mode": checkpoint_storage_mode,
        "recovery_source": recovery_source,
        "replay_snapshot_ref": replay_snapshot_ref,
        "event_segment_refs": event_segment_refs or [],
        "global_state_refs": global_state_refs or [],
        "idempotency_store_ref": idempotency_store_ref,
        "artifact_manifest_ref": artifact_manifest_ref,
        "required_artifact_hashes": required_artifact_hashes or {},
        "compaction_watermarks": compaction_watermarks or {},
        "previous_recovery_manifest_hash": previous_recovery_manifest_hash,
    }
    payload["manifest_hash"] = sha256_json(_hash_payload(payload))
    return RecoveryManifest.model_validate(payload)


def validate_recovery_manifest(manifest: RecoveryManifest) -> None:
    if manifest.schema_version != RECOVERY_MANIFEST_SCHEMA_VERSION:
        raise InvariantViolation("unknown recovery manifest schema")
    expected = sha256_json(_hash_payload(manifest.model_dump(mode="json")))
    if expected != manifest.manifest_hash:
        raise InvariantViolation("recovery manifest_hash mismatch")
    checkpoint_path = manifest.checkpoint_ref.get("path") or manifest.checkpoint_ref.get(
        "manifest_path"
    )
    if checkpoint_path and not Path(str(checkpoint_path)).exists():
        raise InvariantViolation(f"missing recovery checkpoint artifact: {checkpoint_path}")
    for path_str, expected_hash in manifest.required_artifact_hashes.items():
        path = Path(path_str)
        if not path.exists():
            raise InvariantViolation(f"missing required recovery artifact: {path}")
        from decodilo.storage.checksums import sha256_file

        if path.is_file() and sha256_file(path) != expected_hash:
            raise InvariantViolation(f"recovery artifact hash mismatch: {path}")


def write_recovery_manifest_atomic(path: str | Path, manifest: RecoveryManifest) -> None:
    validate_recovery_manifest(manifest)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(
        json.dumps(manifest.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    tmp.replace(target)


def load_recovery_manifest(path: str | Path) -> RecoveryManifest:
    manifest = RecoveryManifest.model_validate_json(Path(path).read_text(encoding="utf-8"))
    validate_recovery_manifest(manifest)
    return manifest
