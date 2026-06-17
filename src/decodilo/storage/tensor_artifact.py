"""Read and write tensor_binary_v1 artifacts."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import numpy as np

from decodilo.errors import InvariantViolation
from decodilo.runtime.artifact_transport import ArtifactRef, LocalArtifactTransport
from decodilo.storage.artifact_writer import write_binary_artifact
from decodilo.storage.chunk_store import ChunkStore
from decodilo.storage.manifest import StorageArtifactManifest
from decodilo.storage.tensor_binary_format import (
    TENSOR_BINARY_CODEC,
    TensorBinaryMetadata,
    tensor_metadata_from_manifest_metadata,
)
from decodilo.storage.tensor_codec import decode_tensors, encode_tensors


def write_tensor_artifact(
    *,
    tensors: Mapping[str, np.ndarray],
    run_id: str,
    artifact_id: str,
    artifact_type: str,
    transport: LocalArtifactTransport,
    manifest_path: str | Path,
    chunk_root: str | Path,
    chunk_size_bytes: int,
    created_by: str,
    require_finite: bool = True,
    metadata: dict | None = None,
) -> ArtifactRef:
    encoded = encode_tensors(
        tensors,
        chunk_size_bytes=chunk_size_bytes,
        created_by=created_by,
        require_finite=require_finite,
        metadata=metadata,
    )
    manifest = write_binary_artifact(
        store=ChunkStore(chunk_root),
        data=encoded.data,
        artifact_id=artifact_id,
        artifact_type=artifact_type,
        run_id=run_id,
        chunk_size_bytes=chunk_size_bytes,
        metadata={
            "codec": TENSOR_BINARY_CODEC,
            "tensor_binary": encoded.metadata.model_dump(mode="json"),
            **(metadata or {}),
        },
        manifest_path=manifest_path,
    )
    return transport.make_ref(
        manifest=manifest,
        manifest_path=manifest_path,
        chunk_root=chunk_root,
        created_by=created_by,
    )


def read_tensor_artifact(
    *,
    ref: ArtifactRef | dict,
    transport: LocalArtifactTransport,
    require_finite: bool | None = None,
) -> tuple[dict[str, np.ndarray], TensorBinaryMetadata]:
    manifest = transport.validate_ref(ref)
    return decode_tensor_manifest(
        manifest=manifest,
        data=transport.read_bytes(ref),
        require_finite=require_finite,
    )


def decode_tensor_manifest(
    *,
    manifest: StorageArtifactManifest,
    data: bytes,
    require_finite: bool | None = None,
) -> tuple[dict[str, np.ndarray], TensorBinaryMetadata]:
    if manifest.metadata.get("codec") != TENSOR_BINARY_CODEC:
        raise InvariantViolation("artifact is not tensor_binary_v1")
    metadata = tensor_metadata_from_manifest_metadata(manifest.metadata)
    tensors = decode_tensors(data, metadata, require_finite=require_finite)
    total_tensor_bytes = sum(spec.byte_length for spec in metadata.tensors)
    if total_tensor_bytes != manifest.total_bytes:
        raise InvariantViolation("tensor byte length does not match artifact total bytes")
    return tensors, metadata
