from pathlib import Path

from decodilo.storage.remote_backend_sdk_guard import scan_project_for_remote_sdk_dependencies


def test_m017_project_has_no_real_remote_sdk_dependencies() -> None:
    report = scan_project_for_remote_sdk_dependencies(Path("."))

    assert report.passed is True
    assert report.forbidden_dependencies == []
    assert report.forbidden_imports == []
    assert report.cloud_env_reads == []
