"""Trainer fragment helpers for tensor_binary_v1 artifacts.

This module is intentionally a thin wrapper around the generic fragment
artifact path. Keeping it explicit makes the binary transport surface easy to
audit without introducing a second serialization implementation.
"""

from __future__ import annotations

from pathlib import Path

from decodilo.errors import InvariantViolation
from decodilo.runtime.artifact_transport import ArtifactRef, LocalArtifactTransport
from decodilo.storage.tensor_binary_format import TENSOR_BINARY_CODEC
from decodilo.trainer.fragment_artifacts import read_fragment_artifact, write_fragment_artifact
from decodilo.trainer.state import TrainerFragment


def write_binary_fragment_artifact(
    *,
    fragment: TrainerFragment,
    transport: LocalArtifactTransport,
    manifest_path: str | Path,
    chunk_root: str | Path,
    chunk_size_bytes: int,
    created_by: str,
) -> ArtifactRef:
    """Write a trainer fragment as a tensor_binary_v1 artifact."""

    return write_fragment_artifact(
        fragment=fragment,
        transport=transport,
        manifest_path=manifest_path,
        chunk_root=chunk_root,
        chunk_size_bytes=chunk_size_bytes,
        created_by=created_by,
        codec="binary_v1",
    )


def read_binary_fragment_artifact(
    *,
    ref: ArtifactRef | dict,
    transport: LocalArtifactTransport,
) -> TrainerFragment:
    """Read and validate a tensor_binary_v1 trainer fragment artifact."""

    manifest = transport.validate_ref(ref)
    if manifest.metadata.get("codec") != TENSOR_BINARY_CODEC:
        raise InvariantViolation("fragment artifact is not tensor_binary_v1")
    return read_fragment_artifact(ref=ref, transport=transport)
