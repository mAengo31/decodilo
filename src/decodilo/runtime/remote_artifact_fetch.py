"""Remote artifact bundle materialization for cross-instance chunked transport."""

from __future__ import annotations

import base64
from typing import Any

from decodilo.errors import InvariantViolation
from decodilo.runtime.artifact_transport import ArtifactRef, LocalArtifactTransport
from decodilo.storage.checksums import sha256_bytes
from decodilo.storage.chunk_store import ChunkStore
from decodilo.storage.manifest import StorageArtifactManifest


def artifact_bundle_from_ref(
    ref: ArtifactRef | dict[str, Any],
    *,
    transport: LocalArtifactTransport,
) -> dict[str, Any]:
    """Build a JSON-safe artifact bundle from a local artifact ref."""

    artifact_ref = ref if isinstance(ref, ArtifactRef) else ArtifactRef.model_validate(ref)
    manifest = transport.validate_ref(artifact_ref)
    _, chunk_root = transport.resolve_ref_paths(artifact_ref)
    store = ChunkStore(chunk_root)
    return {
        "artifact_ref": artifact_ref.model_dump(mode="json"),
        "manifest": manifest.model_dump(mode="json"),
        "chunks": [
            {
                "sha256": chunk_hash,
                "data_b64": base64.b64encode(store.cas.get_bytes(chunk_hash)).decode("ascii"),
            }
            for chunk_hash in manifest.chunk_hashes
        ],
    }


def materialize_artifact_bundle(
    bundle: dict[str, Any],
    *,
    transport: LocalArtifactTransport,
) -> ArtifactRef:
    """Materialize a fetched artifact bundle into ``transport``'s local workdir."""

    artifact_ref = ArtifactRef.model_validate(bundle["artifact_ref"])
    manifest = StorageArtifactManifest.model_validate(bundle["manifest"])
    if manifest.manifest_hash != artifact_ref.manifest_hash:
        raise InvariantViolation("fetched artifact manifest_hash mismatch")
    if manifest.root_hash != artifact_ref.content_root_hash:
        raise InvariantViolation("fetched artifact content root hash mismatch")
    if manifest.total_bytes != artifact_ref.total_bytes:
        raise InvariantViolation("fetched artifact total_bytes mismatch")

    manifest_path = transport._resolve_ref_path(artifact_ref.manifest_path)  # noqa: SLF001
    chunk_root = transport._resolve_ref_path(artifact_ref.chunk_root)  # noqa: SLF001
    store = ChunkStore(chunk_root)

    chunks = list(bundle.get("chunks") or [])
    by_hash = {str(item.get("sha256")): str(item.get("data_b64")) for item in chunks}
    for chunk_hash in manifest.chunk_hashes:
        encoded = by_hash.get(chunk_hash)
        if encoded is None:
            raise InvariantViolation(f"fetched artifact missing chunk {chunk_hash}")
        data = base64.b64decode(encoded.encode("ascii"), validate=True)
        if sha256_bytes(data) != chunk_hash:
            raise InvariantViolation(f"fetched artifact chunk checksum mismatch {chunk_hash}")
        written_hash = store.cas.put_bytes(data)
        if written_hash != chunk_hash:
            raise InvariantViolation(f"materialized artifact chunk hash mismatch {chunk_hash}")

    store.write_manifest(manifest_path, manifest)
    transport.validate_ref(artifact_ref)
    return artifact_ref
