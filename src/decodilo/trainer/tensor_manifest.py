"""Typed manifest for deterministic named tensor flattening."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

TENSOR_MANIFEST_VERSION = "v1"


def stable_json(data: Any) -> str:
    """Return canonical JSON for checksums and persisted metadata."""

    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def sha256_json(data: Any) -> str:
    return hashlib.sha256(stable_json(data).encode("utf-8")).hexdigest()


class TensorSpec(BaseModel):
    """Portable metadata for one named tensor."""

    model_config = ConfigDict(frozen=True)

    name: str
    dtype: str
    shape: list[int]
    offset: int = Field(ge=0)
    length: int = Field(ge=0)
    checksum: str
    device: str | None = "cpu"


class TensorManifest(BaseModel):
    """A deterministic manifest for all tensors in a model state."""

    model_config = ConfigDict(frozen=True)

    schema_version: str = TENSOR_MANIFEST_VERSION
    global_version: int = Field(ge=0)
    total_elements: int = Field(ge=0)
    tensors: list[TensorSpec]
    checksum: str


class FragmentCodecMetadata(BaseModel):
    """Metadata tying flat fragments back to a tensor manifest."""

    model_config = ConfigDict(frozen=True)

    codec_version: str = TENSOR_MANIFEST_VERSION
    manifest_checksum: str
    fragment_count: int = Field(gt=0)
    total_elements: int = Field(ge=0)


def manifest_checksum_payload(
    *,
    global_version: int,
    total_elements: int,
    tensors: list[TensorSpec],
) -> dict[str, Any]:
    return {
        "schema_version": TENSOR_MANIFEST_VERSION,
        "global_version": global_version,
        "total_elements": total_elements,
        "tensors": [tensor.model_dump(mode="json") for tensor in tensors],
    }


def make_manifest(
    *,
    global_version: int,
    total_elements: int,
    tensors: list[TensorSpec],
) -> TensorManifest:
    payload = manifest_checksum_payload(
        global_version=global_version,
        total_elements=total_elements,
        tensors=tensors,
    )
    return TensorManifest(
        global_version=global_version,
        total_elements=total_elements,
        tensors=tensors,
        checksum=sha256_json(payload),
    )


def validate_manifest(manifest: TensorManifest) -> None:
    from decodilo.errors import InvariantViolation

    if manifest.schema_version != TENSOR_MANIFEST_VERSION:
        raise InvariantViolation(f"unknown tensor manifest version {manifest.schema_version!r}")
    expected = sha256_json(
        manifest_checksum_payload(
            global_version=manifest.global_version,
            total_elements=manifest.total_elements,
            tensors=manifest.tensors,
        )
    )
    if expected != manifest.checksum:
        raise InvariantViolation("tensor manifest checksum mismatch")
    offset = 0
    for spec in manifest.tensors:
        if spec.offset != offset:
            raise InvariantViolation("tensor manifest has gap or overlap")
        offset += spec.length
    if offset != manifest.total_elements:
        raise InvariantViolation("tensor manifest length does not match total elements")
