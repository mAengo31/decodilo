from decodilo.storage.durable_object_backend import DurableFilesystemObjectStoreBackend
from decodilo.storage.local_backend import LocalFilesystemArtifactBackend


def test_local_artifact_backend_write_read_and_capabilities(tmp_path) -> None:
    backend = LocalFilesystemArtifactBackend(tmp_path)
    ref = backend.write_bytes(artifact_id="artifact", data=b"payload")

    assert backend.read_bytes(ref) == b"payload"
    assert backend.list_refs() == [ref]
    capabilities = backend.capabilities()
    assert capabilities.local_filesystem is True
    assert capabilities.remote is False
    assert capabilities.model_dump(mode="json")["backend_type"] == "local_filesystem"


def test_durable_object_backend_write_read_and_capabilities(tmp_path) -> None:
    backend = DurableFilesystemObjectStoreBackend(tmp_path)
    ref = backend.write_bytes(artifact_id="artifact", data=b"payload")

    assert backend.read_bytes(ref) == b"payload"
    assert backend.read_range(ref, offset=0, length=4) == b"payl"
    assert backend.list_refs() == [ref]
    capabilities = backend.capabilities()
    assert capabilities.local_filesystem is True
    assert capabilities.remote is False
    assert capabilities.model_dump(mode="json")["backend_type"] == (
        "durable_filesystem_object_store"
    )

