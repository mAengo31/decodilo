"""Memory-map-friendly reader for local tensor artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from decodilo.errors import InvariantViolation
from decodilo.storage.chunk_store import ChunkStore
from decodilo.storage.manifest import StorageArtifactManifest
from decodilo.storage.tensor_artifact import decode_tensor_manifest
from decodilo.storage.tensor_binary_format import TensorBinaryMetadata


@dataclass
class TensorArtifactReadStats:
    bytes_read: int = 0
    chunks_read: int = 0
    mmap_used: bool = False


class MMapTensorArtifactReader:
    """Iterates local artifact chunks and reconstructs tensor_binary_v1 tensors."""

    def __init__(self, *, chunk_root: str | Path, manifest: StorageArtifactManifest) -> None:
        self.store = ChunkStore(chunk_root)
        self.manifest = manifest
        self.stats = TensorArtifactReadStats()

    def iter_tensor_chunks(self):
        self.store.verify_manifest(self.manifest)
        for chunk_hash in self.manifest.chunk_hashes:
            data = self.store.cas.get_bytes(chunk_hash)
            self.stats.bytes_read += len(data)
            self.stats.chunks_read += 1
            yield data

    def validate_only(self) -> TensorArtifactReadStats:
        self.store.verify_manifest(self.manifest)
        self.stats.bytes_read = 0
        self.stats.chunks_read = len(self.manifest.chunk_hashes)
        return self.stats

    def read_tensors(self) -> tuple[dict[str, np.ndarray], TensorBinaryMetadata]:
        data = b"".join(self.iter_tensor_chunks())
        if len(data) != self.manifest.total_bytes:
            raise InvariantViolation("artifact byte count mismatch")
        return decode_tensor_manifest(manifest=self.manifest, data=data)

    def read_tensor(self, name: str) -> np.ndarray:
        tensors, _ = self.read_tensors()
        try:
            return tensors[name]
        except KeyError as exc:
            raise InvariantViolation(f"tensor {name!r} not found") from exc

    def read_flat_fragment_chunks(self):
        return self.iter_tensor_chunks()
