"""Storage-layer errors."""

from __future__ import annotations

from decodilo.errors import DecodiloError


class StorageError(DecodiloError):
    """Base storage error."""


class ChunkMissingError(StorageError):
    """Raised when an artifact references a missing chunk."""


class ChunkCorruptionError(StorageError):
    """Raised when chunk bytes do not match their content hash."""


class ArtifactManifestError(StorageError):
    """Raised when an artifact manifest is invalid."""


class MemoryBudgetExceeded(StorageError):
    """Raised when memory/spill limits reject a payload."""


class SpillError(StorageError):
    """Raised when spill-to-disk cannot be completed safely."""

