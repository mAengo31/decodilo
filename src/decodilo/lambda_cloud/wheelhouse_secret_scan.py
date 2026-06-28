"""Secret scanning for M068W wheelhouses."""

from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.wheelhouse_manifest import load_lambda_wheelhouse_manifest


class LambdaWheelhouseSecretScan(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M068W"
    secret_scan_passed: bool
    scanned_files: int
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_non_launching(self) -> LambdaWheelhouseSecretScan:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("wheelhouse secret scan must not enable launch or spend")
        if self.secret_scan_passed and self.blockers:
            raise ValueError("passing wheelhouse secret scan cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def scan_lambda_wheelhouse_secrets_from_paths(
    *,
    wheelhouse_dir: str | Path,
    manifest: str | Path,
) -> LambdaWheelhouseSecretScan:
    man = load_lambda_wheelhouse_manifest(manifest)
    blockers = [*man.blockers]
    scanned = 0
    base = Path(wheelhouse_dir)
    if not base.exists():
        blockers.append("wheelhouse_dir_missing")
    for wheel in sorted(base.glob("*.whl")) if base.exists() else []:
        scanned += 1
        try:
            with zipfile.ZipFile(wheel) as archive:
                for name in archive.namelist():
                    if _forbidden_member(name):
                        blockers.append(f"forbidden_member:{wheel.name}:{name}")
                    if not _text_member(name):
                        continue
                    content = archive.read(name)
                    if len(content) > 512_000:
                        continue
                    text = content.decode("utf-8", errors="ignore")
                    for hit in _secret_hits(text):
                        blockers.append(f"secret_{hit}:{wheel.name}:{name}")
        except zipfile.BadZipFile:
            blockers.append(f"wheel_zip_unreadable:{wheel.name}")
    return LambdaWheelhouseSecretScan(
        secret_scan_passed=not blockers,
        scanned_files=scanned,
        blockers=sorted(set(blockers)),
        warnings=["wheelhouse secret scan is local-only and does not install packages"],
    )


def load_lambda_wheelhouse_secret_scan(path: str | Path) -> LambdaWheelhouseSecretScan:
    return LambdaWheelhouseSecretScan.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_wheelhouse_secret_scan(
    path: str | Path,
    report: LambdaWheelhouseSecretScan,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")


def _forbidden_member(name: str) -> bool:
    path = Path(name)
    parts = set(path.parts)
    if parts & {".git", ".pytest_cache", ".ruff_cache"}:
        return True
    return path.name == ".env" or path.name.endswith((".pem", ".key", ".ppk"))


def _text_member(name: str) -> bool:
    return Path(name).suffix.lower() in {
        ".py",
        ".txt",
        ".json",
        ".toml",
        ".cfg",
        ".ini",
        ".md",
        "",
    } or name.endswith(("METADATA", "RECORD", "WHEEL"))


def _secret_hits(text: str) -> list[str]:
    patterns = {
        "private_key_material": r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
        "authorization_bearer_value": r"Authorization:\s*Bearer\s+[A-Za-z0-9._~+/=-]{16,}",
        "api_key_value": r"api[_-]?key\s*[:=]\s*[A-Za-z0-9._~+/=-]{16,}",
        "password_value": r"password\s*[:=]\s*[A-Za-z0-9._~+/=-]{12,}",
    }
    return [
        name for name, pattern in patterns.items() if re.search(pattern, text, re.IGNORECASE)
    ]
