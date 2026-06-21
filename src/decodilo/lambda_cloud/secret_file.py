"""Explicit local secret-file loading for Lambda read-only discovery."""

from __future__ import annotations

import hashlib
import json
import stat
import subprocess
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.credential_model import LambdaCredentialError

LambdaSecretSourceKind = Literal["api_key_file", "env_file"]


class LambdaAPISecretFileRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: Path
    basename: str
    redacted: bool = True


class LambdaEnvFileSecretRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: Path
    basename: str
    env_key: str
    git_tracking_status: str | None = None
    gitignored: bool | None = None
    redacted: bool = True


class LambdaAPISecretLoadResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    secret_source: LambdaSecretSourceKind = "api_key_file"
    key_file: LambdaAPISecretFileRef
    secret_loaded: bool
    key_sha256_prefix: str | None = None
    redacted: bool = True
    warnings: list[str] = Field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


class LambdaEnvFileSecretLoadResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    secret_source: LambdaSecretSourceKind = "env_file"
    env_file: LambdaEnvFileSecretRef
    secret_loaded: bool
    redacted: bool = True
    warnings: list[str] = Field(default_factory=list)

    @property
    def env_file_basename(self) -> str:
        return self.env_file.basename

    @property
    def env_key(self) -> str:
        return self.env_file.env_key

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


class LambdaSecretHandlingPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    max_secret_file_bytes: int = Field(default=4096, gt=0)
    max_env_file_bytes: int = Field(default=65536, gt=0)
    reject_world_readable: bool = True
    allow_multiline: bool = False
    env_reads_allowed: bool = False
    raw_cli_secret_allowed: bool = False
    fail_if_env_file_tracked: bool = False


class LambdaSecretAuditReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    passed: bool
    secret_loaded: bool
    redacted: bool = True
    key_sha256_prefix: str | None = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False


def load_lambda_api_key_from_file(
    path: str | Path,
    *,
    policy: LambdaSecretHandlingPolicy | None = None,
) -> tuple[str, LambdaAPISecretLoadResult]:
    policy = policy or LambdaSecretHandlingPolicy()
    if policy.env_reads_allowed or policy.raw_cli_secret_allowed:
        raise LambdaCredentialError("Lambda secrets may only be loaded from explicit files")
    source = Path(path)
    warnings: list[str] = []
    if not source.exists():
        raise LambdaCredentialError("Lambda API key file is missing")
    if source.is_dir():
        raise LambdaCredentialError("Lambda API key file path is a directory")
    size = source.stat().st_size
    if size <= 0:
        raise LambdaCredentialError("Lambda API key file is empty")
    if size > policy.max_secret_file_bytes:
        raise LambdaCredentialError("Lambda API key file is too large")
    mode = stat.S_IMODE(source.stat().st_mode)
    if mode & 0o004:
        if policy.reject_world_readable:
            raise LambdaCredentialError("Lambda API key file must not be world-readable")
        warnings.append("Lambda API key file is world-readable")
    secret = source.read_text(encoding="utf-8").strip()
    if not secret:
        raise LambdaCredentialError("Lambda API key file is empty after trimming")
    if not policy.allow_multiline and "\n" in source.read_text(encoding="utf-8").strip("\n"):
        raise LambdaCredentialError("Lambda API key file must contain a single line")
    prefix = hashlib.sha256(secret.encode("utf-8")).hexdigest()[:8]
    result = LambdaAPISecretLoadResult(
        key_file=LambdaAPISecretFileRef(path=source, basename=source.name),
        secret_loaded=True,
        key_sha256_prefix=prefix,
        warnings=warnings,
    )
    return secret, result


def load_lambda_api_key_from_env_file(
    path: str | Path,
    *,
    env_key: str = "LAMBDA_API_KEY",
    policy: LambdaSecretHandlingPolicy | None = None,
) -> tuple[str, LambdaEnvFileSecretLoadResult]:
    policy = policy or LambdaSecretHandlingPolicy()
    if policy.env_reads_allowed or policy.raw_cli_secret_allowed:
        raise LambdaCredentialError("Lambda env-file secrets require explicit file input")
    if not env_key or "=" in env_key or "\n" in env_key:
        raise LambdaCredentialError("Lambda env key is invalid")
    source = Path(path)
    warnings: list[str] = []
    if not source.exists():
        raise LambdaCredentialError("Lambda env file is missing")
    if source.is_dir():
        raise LambdaCredentialError("Lambda env file path is a directory")
    size = source.stat().st_size
    if size <= 0:
        raise LambdaCredentialError("Lambda env file is empty")
    if size > policy.max_env_file_bytes:
        raise LambdaCredentialError("Lambda env file is too large")
    git_status, gitignored = _git_secret_file_status(source)
    if git_status == "tracked":
        message = "HIGH-SEVERITY: Lambda env file is tracked by git"
        if policy.fail_if_env_file_tracked:
            raise LambdaCredentialError(message)
        warnings.append(message)
    if gitignored is False and git_status != "untracked":
        warnings.append("HIGH-SEVERITY: Lambda env file is neither gitignored nor untracked")
    secret = _parse_env_file_secret(source, env_key=env_key, policy=policy)
    result = LambdaEnvFileSecretLoadResult(
        env_file=LambdaEnvFileSecretRef(
            path=source,
            basename=source.name,
            env_key=env_key,
            git_tracking_status=git_status,
            gitignored=gitignored,
        ),
        secret_loaded=True,
        warnings=warnings,
    )
    return secret, result


def audit_lambda_secret_load(result: LambdaAPISecretLoadResult) -> LambdaSecretAuditReport:
    return LambdaSecretAuditReport(
        passed=result.secret_loaded and result.redacted,
        secret_loaded=result.secret_loaded,
        key_sha256_prefix=result.key_sha256_prefix,
        warnings=result.warnings,
    )


def _parse_env_file_secret(
    path: Path,
    *,
    env_key: str,
    policy: LambdaSecretHandlingPolicy,
) -> str:
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name.strip() != env_key:
            continue
        value = _strip_env_quotes(value.strip())
        if not value:
            raise LambdaCredentialError(f"Lambda env file key {env_key} is empty")
        if not policy.allow_multiline and ("\n" in value or "\r" in value):
            raise LambdaCredentialError("Lambda env file secret must be a single line")
        if len(value.encode("utf-8")) > policy.max_secret_file_bytes:
            raise LambdaCredentialError("Lambda env file secret value is too large")
        return value
    raise LambdaCredentialError(f"Lambda env file did not contain {env_key}")


def _strip_env_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _git_secret_file_status(path: Path) -> tuple[str | None, bool | None]:
    try:
        tracked = subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(path)],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        git_status = "tracked" if tracked.returncode == 0 else "untracked"
        ignored = subprocess.run(
            ["git", "check-ignore", "-q", str(path)],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return git_status, ignored.returncode == 0
    except Exception:  # noqa: BLE001
        return None, None
