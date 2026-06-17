"""Portable named tensor state for trainer adapters."""

from __future__ import annotations

import base64
import hashlib
from collections.abc import Mapping
from typing import Any

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, field_validator

from decodilo.errors import InvariantViolation
from decodilo.trainer.tensor_manifest import (
    TENSOR_MANIFEST_VERSION,
    TensorManifest,
    TensorSpec,
    make_manifest,
    sha256_json,
    stable_json,
    validate_manifest,
)

NAMED_STATE_SCHEMA_VERSION = "v1"


def _array_payload(array: np.ndarray) -> dict[str, Any]:
    normalized = np.ascontiguousarray(array)
    return {
        "dtype": str(normalized.dtype),
        "shape": list(normalized.shape),
        "data_b64": base64.b64encode(normalized.tobytes()).decode("ascii"),
    }


def _array_from_payload(payload: dict[str, Any]) -> np.ndarray:
    dtype = np.dtype(str(payload["dtype"]))
    shape = tuple(int(value) for value in payload["shape"])
    raw = base64.b64decode(str(payload["data_b64"]).encode("ascii"), validate=True)
    expected_bytes = int(np.prod(shape, dtype=np.int64)) * dtype.itemsize
    if len(raw) != expected_bytes:
        raise InvariantViolation("tensor payload byte length does not match dtype and shape")
    return np.frombuffer(raw, dtype=dtype).reshape(shape).copy()


def tensor_checksum(name: str, array: np.ndarray, *, device: str | None = "cpu") -> str:
    payload = _array_payload(array)
    payload.update({"name": name, "device": device or "cpu"})
    return hashlib.sha256(stable_json(payload).encode("utf-8")).hexdigest()


class NamedTensorState(BaseModel):
    """Versioned CPU-portable named tensor state.

    Tensor data is stored as JSON lists for portability. Checksums are computed
    from dtype, shape, name, device label, and canonical raw-byte payload.
    """

    model_config = ConfigDict(frozen=True)

    state_schema_version: str = NAMED_STATE_SCHEMA_VERSION
    global_version: int = Field(ge=0)
    tensors: dict[str, list[Any]]
    manifest: TensorManifest
    checksum: str

    @field_validator("state_schema_version")
    @classmethod
    def _known_schema(cls, value: str) -> str:
        if value != NAMED_STATE_SCHEMA_VERSION:
            raise ValueError(f"unknown named tensor state schema {value!r}")
        return value

    def stable_json(self) -> str:
        return stable_json(self.model_dump(mode="json"))


def named_state_checksum(
    *,
    global_version: int,
    manifest: TensorManifest,
) -> str:
    return sha256_json(
        {
            "state_schema_version": NAMED_STATE_SCHEMA_VERSION,
            "global_version": global_version,
            "manifest_checksum": manifest.checksum,
        }
    )


def named_state_from_numpy(
    tensors: Mapping[str, np.ndarray],
    *,
    global_version: int,
    device: str | None = "cpu",
) -> NamedTensorState:
    """Build a deterministic named tensor state from numpy arrays."""

    if not tensors:
        raise ValueError("named tensor state requires at least one tensor")
    offset = 0
    specs: list[TensorSpec] = []
    data: dict[str, list[Any]] = {}
    for name in sorted(tensors):
        if not name:
            raise ValueError("tensor name must not be empty")
        array = np.asarray(tensors[name])
        if array.size == 0:
            raise ValueError(f"tensor {name!r} must not be empty")
        flat = array.reshape(-1)
        checksum = tensor_checksum(name, array, device=device)
        specs.append(
            TensorSpec(
                name=name,
                dtype=str(array.dtype),
                shape=list(array.shape),
                offset=offset,
                length=int(flat.size),
                checksum=checksum,
                device=device or "cpu",
            )
        )
        data[name] = array.tolist()
        offset += int(flat.size)
    manifest = make_manifest(
        global_version=global_version,
        total_elements=offset,
        tensors=specs,
    )
    return NamedTensorState(
        global_version=global_version,
        tensors=data,
        manifest=manifest,
        checksum=named_state_checksum(global_version=global_version, manifest=manifest),
    )


def tensor_array(state: NamedTensorState, name: str) -> np.ndarray:
    specs = {spec.name: spec for spec in state.manifest.tensors}
    if name not in specs:
        raise KeyError(name)
    spec = specs[name]
    return np.asarray(state.tensors[name], dtype=np.dtype(spec.dtype)).reshape(spec.shape)


def validate_named_state(state: NamedTensorState) -> None:
    if state.state_schema_version != NAMED_STATE_SCHEMA_VERSION:
        raise InvariantViolation(
            f"unknown named tensor state schema {state.state_schema_version!r}"
        )
    validate_manifest(state.manifest)
    expected_state_checksum = named_state_checksum(
        global_version=state.global_version,
        manifest=state.manifest,
    )
    if expected_state_checksum != state.checksum:
        raise InvariantViolation("named tensor state checksum mismatch")
    if state.manifest.schema_version != TENSOR_MANIFEST_VERSION:
        raise InvariantViolation("unknown tensor manifest schema")
    for spec in state.manifest.tensors:
        if spec.name not in state.tensors:
            raise InvariantViolation(f"missing tensor data for {spec.name!r}")
        try:
            array = tensor_array(state, spec.name)
        except (TypeError, ValueError) as exc:
            raise InvariantViolation(f"tensor {spec.name!r} shape mismatch") from exc
        if list(array.shape) != spec.shape:
            raise InvariantViolation(f"tensor {spec.name!r} shape mismatch")
        if str(array.dtype) != spec.dtype:
            raise InvariantViolation(f"tensor {spec.name!r} dtype mismatch")
        if int(array.size) != spec.length:
            raise InvariantViolation(f"tensor {spec.name!r} length mismatch")
        expected = tensor_checksum(spec.name, array, device=spec.device)
        if expected != spec.checksum:
            raise InvariantViolation(f"tensor {spec.name!r} checksum mismatch")
    extra_names = set(state.tensors) - {spec.name for spec in state.manifest.tensors}
    if extra_names:
        raise InvariantViolation(f"tensor data contains names missing from manifest: {extra_names}")
