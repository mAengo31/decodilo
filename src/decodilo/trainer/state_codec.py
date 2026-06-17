"""Stable trainer state and fragment serialization.

The codec intentionally uses JSON plus explicit dtype/shape metadata. It does
not use pickle and does not execute code during decoding.
"""

from __future__ import annotations

import base64
import hashlib
import json
from typing import Any

import numpy as np
from pydantic import ValidationError

from decodilo.errors import InvariantViolation
from decodilo.trainer.state import TrainerFragment, TrainerState

TRAINER_CODEC_VERSION = "v1"


def stable_json(data: dict[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def checksum_payload(data: dict[str, Any]) -> str:
    payload = dict(data)
    payload.pop("checksum", None)
    return hashlib.sha256(stable_json(payload).encode("utf-8")).hexdigest()


def array_to_payload(array: np.ndarray) -> dict[str, Any]:
    normalized = np.ascontiguousarray(array)
    return {
        "dtype": str(normalized.dtype),
        "shape": list(normalized.shape),
        "data_b64": base64.b64encode(normalized.tobytes()).decode("ascii"),
    }


def array_from_payload(payload: dict[str, Any]) -> np.ndarray:
    dtype = np.dtype(str(payload["dtype"]))
    shape = tuple(int(value) for value in payload["shape"])
    raw = base64.b64decode(str(payload["data_b64"]).encode("ascii"))
    return np.frombuffer(raw, dtype=dtype).reshape(shape).copy()


def make_state(
    *,
    trainer_type: str,
    run_id: str,
    learner_id: str,
    global_version: int,
    local_step: int,
    tokens_processed: int,
    tokens_since_last_sync: int,
    parameters: np.ndarray,
    metadata: dict[str, Any] | None = None,
    trainer_state_kind: str = "flat",
    tensor_manifest: dict[str, Any] | None = None,
    flat_state_checksum: str | None = None,
    named_state_checksum: str | None = None,
) -> TrainerState:
    array_payload = array_to_payload(np.asarray(parameters, dtype=np.float64))
    payload: dict[str, Any] = {
        "codec_version": TRAINER_CODEC_VERSION,
        "trainer_type": trainer_type,
        "run_id": run_id,
        "learner_id": learner_id,
        "global_version": global_version,
        "local_step": local_step,
        "tokens_processed": tokens_processed,
        "tokens_since_last_sync": tokens_since_last_sync,
        "dtype": array_payload["dtype"],
        "shape": array_payload["shape"],
        "parameters": array_from_payload(array_payload).astype(float).tolist(),
        "metadata": metadata or {},
        "trainer_state_kind": trainer_state_kind,
        "tensor_manifest": tensor_manifest,
        "flat_state_checksum": flat_state_checksum,
        "named_state_checksum": named_state_checksum,
    }
    payload["checksum"] = checksum_payload(payload)
    return TrainerState.model_validate(payload)


def make_fragment(
    *,
    trainer_type: str,
    run_id: str,
    learner_id: str,
    fragment_id: int,
    global_version: int,
    data: np.ndarray,
    tokens: int,
    metadata: dict[str, Any] | None = None,
    trainer_state_kind: str = "flat",
    flat_fragment: dict[str, Any] | None = None,
    tensor_manifest: dict[str, Any] | None = None,
) -> TrainerFragment:
    array = np.asarray(data, dtype=np.float64)
    payload: dict[str, Any] = {
        "codec_version": TRAINER_CODEC_VERSION,
        "trainer_type": trainer_type,
        "run_id": run_id,
        "learner_id": learner_id,
        "fragment_id": fragment_id,
        "global_version": global_version,
        "dtype": str(array.dtype),
        "shape": list(array.shape),
        "data": array.astype(float).tolist(),
        "tokens": tokens,
        "metadata": metadata or {},
        "trainer_state_kind": trainer_state_kind,
        "flat_fragment": flat_fragment,
        "tensor_manifest": tensor_manifest,
    }
    payload["checksum"] = checksum_payload(payload)
    return TrainerFragment.model_validate(payload)


def encode_state(state: TrainerState) -> str:
    return stable_json(state.model_dump(mode="json"))


def decode_state(encoded: str) -> TrainerState:
    try:
        raw = json.loads(encoded)
        state = TrainerState.model_validate(raw)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise InvariantViolation(f"invalid trainer state: {exc}") from exc
    validate_state(state)
    return state


def encode_fragment(fragment: TrainerFragment) -> str:
    return stable_json(fragment.model_dump(mode="json"))


def decode_fragment(encoded: str) -> TrainerFragment:
    try:
        raw = json.loads(encoded)
        fragment = TrainerFragment.model_validate(raw)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise InvariantViolation(f"invalid trainer fragment: {exc}") from exc
    validate_fragment(fragment)
    return fragment


def validate_state(state: TrainerState) -> None:
    if state.codec_version != TRAINER_CODEC_VERSION:
        raise InvariantViolation(f"unknown trainer codec {state.codec_version!r}")
    if checksum_payload(state.model_dump(mode="json")) != state.checksum:
        raise InvariantViolation("trainer state checksum mismatch")
    if list(np.asarray(state.parameters, dtype=np.float64).shape) != state.shape:
        raise InvariantViolation("trainer state shape mismatch")


def validate_fragment(fragment: TrainerFragment) -> None:
    if fragment.codec_version != TRAINER_CODEC_VERSION:
        raise InvariantViolation(f"unknown trainer codec {fragment.codec_version!r}")
    if checksum_payload(fragment.model_dump(mode="json")) != fragment.checksum:
        raise InvariantViolation("trainer fragment checksum mismatch")
    if list(np.asarray(fragment.data, dtype=np.float64).shape) != fragment.shape:
        raise InvariantViolation("trainer fragment shape mismatch")
