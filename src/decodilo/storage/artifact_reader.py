"""Artifact readers for local chunk storage."""

from __future__ import annotations

from pathlib import Path

from decodilo.storage.chunk_store import ChunkStore
from decodilo.storage.manifest import StorageArtifactManifest


class ArtifactReader:
    def __init__(self, *, store: ChunkStore, manifest: StorageArtifactManifest) -> None:
        self.store = store
        self.manifest = manifest

    def read_all(self) -> bytes:
        return self.store.read_bytes(self.manifest)


def read_binary_artifact(
    *,
    store: ChunkStore,
    manifest: StorageArtifactManifest,
) -> bytes:
    return ArtifactReader(store=store, manifest=manifest).read_all()


def load_and_read_binary_artifact(
    *,
    store: ChunkStore,
    manifest_path: str | Path,
) -> bytes:
    return store.read_bytes(store.read_manifest(manifest_path))

