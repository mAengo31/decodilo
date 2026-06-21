import pytest

from decodilo.storage.disabled_remote_backend import (
    DisabledRemoteArtifactBackend,
    RemoteBackendDisabledError,
)


def test_disabled_remote_backend_still_disabled() -> None:
    backend = DisabledRemoteArtifactBackend()

    assert backend.remote_capabilities().remote_backend_enabled is False
    with pytest.raises(RemoteBackendDisabledError):
        backend.list_refs()

