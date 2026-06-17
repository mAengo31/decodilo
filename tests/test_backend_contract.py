from decodilo.storage.backend_contract import check_backend_contract
from decodilo.storage.disabled_remote_backend import DisabledRemoteArtifactBackend
from decodilo.storage.local_backend import LocalFilesystemArtifactBackend


def test_local_backend_satisfies_contract(tmp_path) -> None:
    report = check_backend_contract(LocalFilesystemArtifactBackend(tmp_path))

    assert report.backend_type == "local_filesystem"
    assert report.usable is True
    assert report.remote_backend_enabled is False
    assert all(check.passed for check in report.checks)


def test_disabled_backend_contract_remains_disabled() -> None:
    report = check_backend_contract(DisabledRemoteArtifactBackend())

    assert report.backend_type == "remote_disabled"
    assert report.usable is False
    assert report.remote_backend_enabled is False
    assert any(check.name == "remote_disabled" and check.passed for check in report.checks)
