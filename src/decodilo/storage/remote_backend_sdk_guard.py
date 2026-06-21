"""Guardrails that prevent accidental remote SDK or secret introduction."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

FORBIDDEN_REMOTE_SDK_DEPENDENCIES = [
    "boto3",
    "botocore",
    "google-cloud-storage",
    "azure-storage-blob",
    "s3fs",
    "gcsfs",
    "adlfs",
    "minio",
]
FORBIDDEN_REMOTE_IMPORTS = [
    "boto3",
    "botocore",
    "google.cloud",
    "azure.storage",
    "s3fs",
    "gcsfs",
    "adlfs",
    "minio",
]
FORBIDDEN_ENV_PREFIXES = ["AWS_", "GOOGLE_", "AZURE_", "LAMBDA_", "S3_", "GCS_"]
SECRET_FIELD_NAMES = {
    "secret_value",
    "access_key",
    "secret_key",
    "token",
    "password",
    "private_key",
}
_ENV_ACCESS_MARKERS = ("os." + "environ", "get" + "env(")
_SECRET_VALUE_PATTERN = re.compile(
    r"(AKIA[0-9A-Z]{12,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|[A-Za-z0-9_=-]{80,})"
)


class RemoteBackendSDKGuardReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    passed: bool
    project_root: str
    forbidden_dependencies: list[str] = Field(default_factory=list)
    forbidden_imports: list[str] = Field(default_factory=list)
    cloud_env_reads: list[str] = Field(default_factory=list)
    secret_findings: list[str] = Field(default_factory=list)
    files_scanned: int = 0
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    remote_backend_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def scan_project_for_remote_sdk_dependencies(
    project_root: str | Path,
) -> RemoteBackendSDKGuardReport:
    root = Path(project_root)
    dependency_findings: list[str] = []
    import_findings: list[str] = []
    env_findings: list[str] = []
    files_scanned = 0
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        text = pyproject.read_text(encoding="utf-8")
        files_scanned += 1
        for dep in FORBIDDEN_REMOTE_SDK_DEPENDENCIES:
            if dep in text:
                dependency_findings.append(f"pyproject.toml:{dep}")
    src_root = root / "src" / "decodilo"
    if src_root.exists():
        for path in src_root.rglob("*.py"):
            files_scanned += 1
            text = path.read_text(encoding="utf-8")
            import_findings.extend(_scan_import_lines(path, text))
            env_findings.extend(_scan_env_reads(path, text))
    errors = [
        *[f"forbidden dependency: {item}" for item in dependency_findings],
        *[f"forbidden import: {item}" for item in import_findings],
        *[f"forbidden cloud env read: {item}" for item in env_findings],
    ]
    return RemoteBackendSDKGuardReport(
        passed=not errors,
        project_root=str(root),
        forbidden_dependencies=dependency_findings,
        forbidden_imports=import_findings,
        cloud_env_reads=env_findings,
        files_scanned=files_scanned,
        errors=errors,
        warnings=["guard is static review evidence; it does not enable remote backend"],
    )


def scan_project_for_cloud_env_reads(project_root: str | Path) -> list[str]:
    root = Path(project_root)
    findings: list[str] = []
    for path in root.rglob("*.py"):
        findings.extend(_scan_env_reads(path, path.read_text(encoding="utf-8")))
    return findings


def scan_json_for_secret_like_values(data: Any, *, path: str = "$") -> list[str]:
    findings: list[str] = []
    if isinstance(data, dict):
        for key, value in data.items():
            lowered = str(key).lower()
            child = f"{path}.{key}"
            if lowered in SECRET_FIELD_NAMES:
                findings.append(child)
            findings.extend(scan_json_for_secret_like_values(value, path=child))
    elif isinstance(data, list):
        for index, value in enumerate(data):
            findings.extend(scan_json_for_secret_like_values(value, path=f"{path}[{index}]"))
    elif isinstance(data, str):
        if _SECRET_VALUE_PATTERN.search(data):
            findings.append(path)
    return findings


def load_remote_backend_sdk_guard_report(path: str | Path) -> RemoteBackendSDKGuardReport:
    return RemoteBackendSDKGuardReport.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_remote_backend_sdk_guard_report(
    path: str | Path,
    report: RemoteBackendSDKGuardReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")


def _scan_import_lines(path: Path, text: str) -> list[str]:
    findings: list[str] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped.startswith(("import ", "from ")):
            continue
        for forbidden in FORBIDDEN_REMOTE_IMPORTS:
            if forbidden in stripped:
                findings.append(f"{path}:{line_number}:{forbidden}")
    return findings


def _scan_env_reads(path: Path, text: str) -> list[str]:
    findings: list[str] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if all(marker not in line for marker in _ENV_ACCESS_MARKERS):
            continue
        for prefix in FORBIDDEN_ENV_PREFIXES:
            if prefix in line:
                findings.append(f"{path}:{line_number}:{prefix}")
    return findings
