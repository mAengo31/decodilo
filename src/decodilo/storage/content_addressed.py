"""Local filesystem content-addressed chunk storage."""

from __future__ import annotations

import os
from pathlib import Path

from decodilo.storage.checksums import sha256_bytes
from decodilo.storage.errors import ChunkCorruptionError, ChunkMissingError


class ContentAddressedStore:
    """Stores immutable blobs by SHA-256 under a local root."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.chunk_root = self.root / "chunks"
        self.chunk_root.mkdir(parents=True, exist_ok=True)

    def path_for_hash(self, content_hash: str) -> Path:
        return self.chunk_root / content_hash[:2] / content_hash

    def has(self, content_hash: str) -> bool:
        return self.path_for_hash(content_hash).exists()

    def put_bytes(self, data: bytes) -> str:
        content_hash = sha256_bytes(data)
        target = self.path_for_hash(content_hash)
        if target.exists():
            return content_hash
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(".tmp")
        tmp.write_bytes(data)
        os.replace(tmp, target)
        return content_hash

    def get_bytes(self, content_hash: str) -> bytes:
        target = self.path_for_hash(content_hash)
        if not target.exists():
            raise ChunkMissingError(f"missing chunk {content_hash}")
        data = target.read_bytes()
        if sha256_bytes(data) != content_hash:
            raise ChunkCorruptionError(f"chunk {content_hash} checksum mismatch")
        return data

    def delete(self, content_hash: str) -> None:
        self.path_for_hash(content_hash).unlink(missing_ok=True)

