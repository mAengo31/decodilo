"""Runtime storage mode validation."""

from __future__ import annotations

from typing import Literal

from decodilo.errors import InvariantViolation

PayloadStorageMode = Literal["inline", "chunked", "auto"]
CheckpointStorageMode = Literal["inline", "chunked", "dual"]
MergeMode = Literal["in_memory", "streaming_chunked", "auto"]
GlobalUpdateStorageMode = Literal["inline", "chunked", "auto"]

PAYLOAD_STORAGE_MODES = {"inline", "chunked", "auto"}
CHECKPOINT_STORAGE_MODES = {"inline", "chunked", "dual"}
MERGE_MODES = {"in_memory", "streaming_chunked", "auto"}
GLOBAL_UPDATE_STORAGE_MODES = {"inline", "chunked", "auto"}


def validate_runtime_modes(
    *,
    payload_storage_mode: str,
    checkpoint_storage_mode: str,
    merge_mode: str,
    global_update_storage_mode: str,
) -> None:
    if payload_storage_mode not in PAYLOAD_STORAGE_MODES:
        raise InvariantViolation(f"invalid payload_storage_mode {payload_storage_mode!r}")
    if checkpoint_storage_mode not in CHECKPOINT_STORAGE_MODES:
        raise InvariantViolation(f"invalid checkpoint_storage_mode {checkpoint_storage_mode!r}")
    if merge_mode not in MERGE_MODES:
        raise InvariantViolation(f"invalid merge_mode {merge_mode!r}")
    if global_update_storage_mode not in GLOBAL_UPDATE_STORAGE_MODES:
        raise InvariantViolation(
            f"invalid global_update_storage_mode {global_update_storage_mode!r}"
        )
    if merge_mode == "streaming_chunked" and payload_storage_mode == "inline":
        raise InvariantViolation(
            "merge_mode=streaming_chunked requires chunked or auto payload storage"
        )


def should_use_chunked_payload(
    *,
    mode: str,
    payload_bytes: int,
    inline_payload_max_bytes: int,
) -> bool:
    if mode == "chunked":
        return True
    if mode == "inline":
        return False
    if mode != "auto":
        raise InvariantViolation(f"invalid payload storage mode {mode!r}")
    return payload_bytes > inline_payload_max_bytes

