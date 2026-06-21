import json
from pathlib import Path

from decodilo.storage.remote_backend_sdk_guard import (
    scan_json_for_secret_like_values,
    scan_project_for_remote_sdk_dependencies,
)


def test_current_project_passes_sdk_guard() -> None:
    report = scan_project_for_remote_sdk_dependencies(Path("."))

    assert report.passed is True
    assert report.remote_backend_enabled is False
    assert report.launch_allowed is False


def test_synthetic_forbidden_dependency_import_and_env_read_fail(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\ndependencies = ["boto3"]\n',
        encoding="utf-8",
    )
    src = tmp_path / "src" / "decodilo" / "storage"
    src.mkdir(parents=True)
    (src / "bad.py").write_text(
        "import boto3\nimport os\nvalue = os.environ['AWS_ACCESS_KEY_ID']\n",
        encoding="utf-8",
    )

    report = scan_project_for_remote_sdk_dependencies(tmp_path)

    assert report.passed is False
    assert report.forbidden_dependencies
    assert report.forbidden_imports
    assert report.cloud_env_reads


def test_json_secret_scan_detects_forbidden_secret_fields() -> None:
    findings = scan_json_for_secret_like_values(
        json.loads('{"secret_key": "redacted", "nested": {"token": "redacted"}}')
    )

    assert "$.secret_key" in findings
    assert "$.nested.token" in findings
