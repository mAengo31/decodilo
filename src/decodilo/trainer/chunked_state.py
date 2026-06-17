"""Chunked model-state metadata for large-state tests."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from decodilo.storage.checksums import sha256_json


class LazyTensorSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    dtype: str = "float32"
    shape: list[int]
    offset_bytes: int = Field(ge=0)
    length_bytes: int = Field(gt=0)
    bytes_per_element: int = Field(gt=0)
    logical_num_elements: int = Field(gt=0)


class ChunkedStateChunk(BaseModel):
    model_config = ConfigDict(frozen=True)

    tensor_name: str
    chunk_index: int = Field(ge=0)
    logical_offset_bytes: int = Field(ge=0)
    length_bytes: int = Field(gt=0)
    data: bytes
    checksum: str


class ChunkedNamedTensorState(BaseModel):
    model_config = ConfigDict(frozen=True)

    state_schema_version: str = "v1"
    run_id: str
    learner_id: str
    global_version: int = Field(ge=0)
    tensors: list[LazyTensorSpec]
    total_logical_bytes: int = Field(ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)
    manifest_hash: str


def make_chunked_state_manifest(
    *,
    run_id: str,
    learner_id: str,
    global_version: int,
    tensors: list[LazyTensorSpec],
    metadata: dict[str, Any] | None = None,
) -> ChunkedNamedTensorState:
    total = sum(tensor.length_bytes for tensor in tensors)
    payload = {
        "global_version": global_version,
        "learner_id": learner_id,
        "metadata": metadata or {},
        "run_id": run_id,
        "tensors": [tensor.model_dump(mode="json") for tensor in tensors],
        "total_logical_bytes": total,
    }
    return ChunkedNamedTensorState(
        run_id=run_id,
        learner_id=learner_id,
        global_version=global_version,
        tensors=tensors,
        total_logical_bytes=total,
        metadata=metadata or {},
        manifest_hash=sha256_json(payload),
    )

