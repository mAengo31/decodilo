import pytest

from decodilo.storage.artifact_backend import ArtifactBackendRef
from decodilo.storage.disabled_remote_backend import (
    DisabledRemoteArtifactBackend,
    RemoteBackendDisabledError,
)


def test_disabled_remote_backend_raises_for_all_operations() -> None:
    backend = DisabledRemoteArtifactBackend()
    ref = ArtifactBackendRef(backend_type="remote_disabled", uri="disabled://x", artifact_id="x")

    assert backend.capabilities().remote is True
    assert backend.capabilities().write_supported is False
    with pytest.raises(RemoteBackendDisabledError):
        backend.write_bytes(artifact_id="x", data=b"x")
    with pytest.raises(RemoteBackendDisabledError):
        backend.read_bytes(ref)
    with pytest.raises(RemoteBackendDisabledError):
        backend.list_refs()
    with pytest.raises(RemoteBackendDisabledError):
        backend.read_range(ref, offset=0, length=1)
    with pytest.raises(RemoteBackendDisabledError):
        list(backend.iter_chunks(ref))
