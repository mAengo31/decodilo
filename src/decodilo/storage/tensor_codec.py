"""Numpy tensor serialization for tensor_binary_v1 artifacts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np

from decodilo.errors import InvariantViolation
from decodilo.storage.checksums import sha256_bytes
from decodilo.storage.tensor_binary_format import (
    SUPPORTED_DTYPES,
    TENSOR_BINARY_CODEC,
    TensorBinaryMetadata,
    TensorBinarySpec,
)


@dataclass(frozen=True)
class EncodedTensorBundle:
    data: bytes
    metadata: TensorBinaryMetadata


def _canonical_array(array: np.ndarray, *, require_finite: bool) -> np.ndarray:
    raw = np.asarray(array)
    if raw.dtype == object:
        raise InvariantViolation("object dtype is not supported by tensor_binary_v1")
    if raw.dtype.byteorder == ">" and raw.dtype.kind not in {"b", "?"}:
        raw = raw.byteswap().view(raw.dtype.newbyteorder("<"))
    elif raw.dtype.byteorder not in {"<", "|", "="}:
        raw = raw.astype(raw.dtype.newbyteorder("<"), copy=False)
    if raw.dtype.byteorder == "=" and np.little_endian and raw.dtype.kind not in {"b", "?"}:
        raw = raw.astype(raw.dtype.newbyteorder("<"), copy=False)
    dtype_name = str(raw.dtype)
    if dtype_name == "bfloat16":
        raise InvariantViolation("bfloat16 is not supported by tensor_binary_v1")
    if dtype_name not in SUPPORTED_DTYPES:
        raise InvariantViolation(f"unsupported tensor dtype {dtype_name!r}")
    if raw.dtype.kind in {"f", "c"} and require_finite and not np.all(np.isfinite(raw)):
        raise InvariantViolation("tensor contains non-finite values")
    contiguous = np.ascontiguousarray(raw)
    return np.ascontiguousarray(contiguous)


def encode_tensors(
    tensors: Mapping[str, np.ndarray],
    *,
    chunk_size_bytes: int,
    created_by: str,
    require_finite: bool = True,
    metadata: dict | None = None,
) -> EncodedTensorBundle:
    """Encode named numpy tensors into one deterministic byte stream."""

    if chunk_size_bytes <= 0:
        raise ValueError("chunk_size_bytes must be positive")
    if not tensors:
        raise ValueError("at least one tensor is required")
    data_parts: list[bytes] = []
    specs: list[TensorBinarySpec] = []
    byte_offset = 0
    seen: set[str] = set()
    for name in sorted(tensors):
        if name in seen:
            raise InvariantViolation(f"duplicate tensor name {name!r}")
        seen.add(name)
        array = _canonical_array(np.asarray(tensors[name]), require_finite=require_finite)
        raw = array.tobytes(order="C")
        dtype_name = str(array.dtype)
        byte_order = "not_applicable" if array.dtype.kind in {"b", "?"} else "little"
        chunk_start = byte_offset // chunk_size_bytes
        chunk_end = (byte_offset + len(raw) + chunk_size_bytes - 1) // chunk_size_bytes
        specs.append(
            TensorBinarySpec(
                name=name,
                dtype=dtype_name,
                shape=list(array.shape),
                num_elements=int(array.size),
                byte_order=byte_order,
                byte_offset=byte_offset,
                byte_length=len(raw),
                chunk_start=chunk_start,
                chunk_end=chunk_end,
                tensor_checksum=sha256_bytes(raw),
            )
        )
        data_parts.append(raw)
        byte_offset += len(raw)
    binary_metadata = TensorBinaryMetadata(
        created_by=created_by,
        tensors=specs,
        requires_finite=require_finite,
        metadata=metadata or {},
    )
    return EncodedTensorBundle(data=b"".join(data_parts), metadata=binary_metadata)


def decode_tensors(
    data: bytes,
    metadata: TensorBinaryMetadata,
    *,
    require_finite: bool | None = None,
) -> dict[str, np.ndarray]:
    """Decode tensors and validate byte ranges, checksums, dtype, and shape."""

    if metadata.codec != TENSOR_BINARY_CODEC:
        raise InvariantViolation("unsupported tensor binary codec")
    tensors: dict[str, np.ndarray] = {}
    seen: set[str] = set()
    require_finite = metadata.requires_finite if require_finite is None else require_finite
    for spec in metadata.tensors:
        if spec.name in seen:
            raise InvariantViolation(f"duplicate tensor name {spec.name!r}")
        seen.add(spec.name)
        end = spec.byte_offset + spec.byte_length
        if end > len(data):
            raise InvariantViolation("tensor byte range exceeds artifact payload")
        raw = data[spec.byte_offset:end]
        if len(raw) != spec.byte_length:
            raise InvariantViolation("tensor byte length mismatch")
        if sha256_bytes(raw) != spec.tensor_checksum:
            raise InvariantViolation(f"tensor {spec.name!r} checksum mismatch")
        dtype = np.dtype(spec.dtype)
        expected_bytes = spec.num_elements * dtype.itemsize
        if expected_bytes != spec.byte_length:
            raise InvariantViolation(f"tensor {spec.name!r} byte length mismatch")
        array = np.frombuffer(raw, dtype=dtype).reshape(tuple(spec.shape)).copy()
        if dtype.byteorder == ">" and dtype.kind not in {"b", "?"}:
            array = array.byteswap().view(dtype.newbyteorder("<"))
        if dtype.kind in {"f", "c"} and require_finite and not np.all(np.isfinite(array)):
            raise InvariantViolation("tensor contains non-finite values")
        tensors[spec.name] = np.ascontiguousarray(array)
    return tensors
