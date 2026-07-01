from __future__ import annotations

from decodilo.storage.artifact_backend import ArtifactBackendRef
from decodilo.storage.durable_object_backend import DurableFilesystemObjectStoreBackend


def test_durable_filesystem_object_store_survives_reopen_and_supports_ranges(tmp_path) -> None:
    backend = DurableFilesystemObjectStoreBackend(tmp_path, namespace="run-a")
    ref = backend.write_bytes(artifact_id="global-update-v1", data=b"abcdef")

    assert ref.backend_type == "durable_filesystem_object_store"
    assert backend.read_bytes(ref) == b"abcdef"
    assert backend.read_range(ref, offset=1, length=3) == b"bcd"
    assert backend.artifact_size(ref) == 6
    assert backend.list_refs() == [ref]

    reopened = DurableFilesystemObjectStoreBackend(tmp_path, namespace="run-a")
    assert reopened.list_refs() == [ref]
    assert reopened.read_bytes(ref) == b"abcdef"


def test_durable_filesystem_object_store_idempotent_put_and_versioning(tmp_path) -> None:
    backend = DurableFilesystemObjectStoreBackend(tmp_path)
    first = backend.write_bytes(artifact_id="fragment", data=b"payload")
    duplicate = backend.write_bytes(artifact_id="fragment", data=b"payload")
    updated = backend.write_bytes(artifact_id="fragment", data=b"payload-v2")

    assert duplicate == first
    assert first.metadata["version"] == 1
    assert updated.metadata["version"] == 2
    assert backend.read_bytes(updated) == b"payload-v2"


def test_durable_filesystem_object_store_capabilities_are_honest(tmp_path) -> None:
    backend = DurableFilesystemObjectStoreBackend(tmp_path)

    caps = backend.capabilities()
    assert caps.backend_type == "durable_filesystem_object_store"
    assert caps.local_filesystem is True
    assert caps.remote is False
    assert caps.credentials_required is False

    remote_caps = backend.remote_capabilities()
    assert remote_caps.backend_name == "durable_filesystem_object_store"
    assert remote_caps.remote_backend_enabled is False
    assert remote_caps.supports_range_read is True
    assert remote_caps.supports_strong_read_after_write is True


def test_durable_filesystem_object_store_rejects_wrong_backend_ref(tmp_path) -> None:
    backend = DurableFilesystemObjectStoreBackend(tmp_path)
    ref = ArtifactBackendRef(backend_type="other", uri="x", artifact_id="x")

    try:
        backend.read_bytes(ref)
    except ValueError as exc:
        assert "unsupported backend_type" in str(exc)
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("wrong backend ref was accepted")
