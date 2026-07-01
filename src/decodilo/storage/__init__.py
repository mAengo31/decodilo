"""Local chunked artifact storage primitives."""

from decodilo.storage.artifact_reader import ArtifactReader, read_binary_artifact
from decodilo.storage.artifact_writer import ArtifactWriter, write_binary_artifact
from decodilo.storage.chunk_store import ChunkStore
from decodilo.storage.content_addressed import ContentAddressedStore
from decodilo.storage.durable_object_backend import DurableFilesystemObjectStoreBackend
from decodilo.storage.manifest import StorageArtifactManifest
from decodilo.storage.s3_client_factory import (
    S3CompatibleClientFactory,
    create_s3_compatible_backend,
)
from decodilo.storage.s3_compatible_backend import (
    S3CompatibleArtifactBackend,
    S3CompatibleBackendConfig,
)

__all__ = [
    "ArtifactReader",
    "ArtifactWriter",
    "ChunkStore",
    "ContentAddressedStore",
    "DurableFilesystemObjectStoreBackend",
    "S3CompatibleArtifactBackend",
    "S3CompatibleClientFactory",
    "S3CompatibleBackendConfig",
    "StorageArtifactManifest",
    "read_binary_artifact",
    "create_s3_compatible_backend",
    "write_binary_artifact",
]
