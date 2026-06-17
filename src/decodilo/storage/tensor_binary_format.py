"""Safe binary tensor artifact format models.

The binary format stores raw tensor bytes in content-addressed chunks and keeps
all executable-free metadata in deterministic JSON manifests.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from decodilo.errors import InvariantViolation
from decodilo.storage.checksums import sha256_json, stable_json

TENSOR_BINARY_CODEC = "tensor_binary_v1"
TENSOR_BINARY_SCHEMA_VERSION = "v1"

SUPPORTED_DTYPES = {
    "float16",
    "float32",
    "float64",
    "int8",
    "int16",
    "int32",
    "int64",
    "uint8",
    "bool",
}

ByteOrder = Literal["little", "big", "not_applicable"]


class TensorBinarySpec(BaseModel):
    """Metadata for one tensor inside a binary artifact byte stream."""

    model_config = ConfigDict(frozen=True)

    name: str
    dtype: str
    shape: list[int]
    num_elements: int = Field(ge=0)
    byte_order: ByteOrder
    byte_offset: int = Field(ge=0)
    byte_length: int = Field(ge=0)
    chunk_start: int = Field(ge=0)
    chunk_end: int = Field(ge=0)
    tensor_checksum: str

    @field_validator("name")
    @classmethod
    def _name_nonempty(cls, value: str) -> str:
        if not value:
            raise ValueError("tensor name must not be empty")
        return value

    @field_validator("dtype")
    @classmethod
    def _dtype_supported(cls, value: str) -> str:
        if value == "bfloat16":
            raise ValueError("bfloat16 is not supported by tensor_binary_v1")
        if value not in SUPPORTED_DTYPES:
            raise ValueError(f"unsupported tensor dtype {value!r}")
        return value

    @field_validator("shape")
    @classmethod
    def _shape_valid(cls, value: list[int]) -> list[int]:
        if not value:
            raise ValueError("tensor shape must not be empty")
        if any(dim < 0 for dim in value):
            raise ValueError("tensor shape dimensions must be non-negative")
        return value

    @model_validator(mode="after")
    def _ranges_valid(self) -> TensorBinarySpec:
        if self.chunk_end < self.chunk_start:
            raise ValueError("chunk_end must be >= chunk_start")
        expected = 1
        for dim in self.shape:
            expected *= dim
            if expected > 2**63 - 1:
                raise ValueError("tensor shape is too large")
        if expected != self.num_elements:
            raise ValueError("tensor num_elements does not match shape")
        return self


class TensorBinaryMetadata(BaseModel):
    """StorageArtifactManifest metadata payload for tensor_binary_v1."""

    model_config = ConfigDict(frozen=True)

    codec: Literal["tensor_binary_v1"] = TENSOR_BINARY_CODEC
    tensor_binary_schema_version: Literal["v1"] = TENSOR_BINARY_SCHEMA_VERSION
    created_by: str
    tensors: list[TensorBinarySpec]
    requires_finite: bool = True
    byte_order: ByteOrder = "little"
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _tensor_layout_valid(self) -> TensorBinaryMetadata:
        names = [tensor.name for tensor in self.tensors]
        if len(set(names)) != len(names):
            raise ValueError("duplicate tensor names are not allowed")
        offset = 0
        for tensor in sorted(self.tensors, key=lambda item: item.byte_offset):
            if tensor.byte_offset != offset:
                raise ValueError("tensor byte ranges must be contiguous and non-overlapping")
            offset += tensor.byte_length
        return self

    def stable_json(self) -> str:
        return stable_json(self.model_dump(mode="json"))

    def metadata_hash(self) -> str:
        return sha256_json(self.model_dump(mode="json"))


def tensor_metadata_from_manifest_metadata(metadata: dict[str, Any]) -> TensorBinaryMetadata:
    try:
        return TensorBinaryMetadata.model_validate(metadata["tensor_binary"])
    except Exception as exc:
        raise InvariantViolation(f"invalid tensor_binary_v1 metadata: {exc}") from exc
