"""Bounded redacted stderr capture policy for SSH probe failures."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

MAX_STDERR_BYTES = 8192
MAX_STDERR_LINES = 80

_SECRET_PATTERNS = (
    re.compile(r"Authorization:\s*Bearer\s+\S+", re.IGNORECASE),
    re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]+", re.IGNORECASE),
    re.compile(r"(api[_-]?key\s*[=:]\s*)\S+", re.IGNORECASE),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S),
    re.compile(r"\bssh-(?:rsa|ed25519)\s+[A-Za-z0-9+/=]+(?:\s+\S+)?"),
    re.compile(r"\becdsa-sha2-[^\s]+\s+[A-Za-z0-9+/=]+(?:\s+\S+)?"),
)


class LambdaSSHFailureStderrCaptureReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    capture_policy_status: str
    max_stderr_bytes: int = MAX_STDERR_BYTES
    max_lines: int = MAX_STDERR_LINES
    stdout_should_remain_empty: bool = True
    stderr_redacted: str | None = None
    stderr_sha256_prefix: str | None = None
    stderr_truncated: bool = False
    secret_scan_passed: bool
    redaction_patterns_applied: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_capture(self) -> LambdaSSHFailureStderrCaptureReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or not self.stdout_should_remain_empty
        ):
            raise ValueError("stderr capture policy cannot enable execution")
        if self.capture_policy_status == "policy_defined" and self.blockers:
            raise ValueError("passing stderr capture policy cannot include blockers")
        if self.stderr_redacted and _contains_secret_marker(self.stderr_redacted):
            raise ValueError("redacted stderr still contains secret-like material")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_ssh_stderr_capture_policy() -> LambdaSSHFailureStderrCaptureReport:
    return LambdaSSHFailureStderrCaptureReport(
        capture_policy_status="policy_defined",
        stderr_redacted=None,
        stderr_sha256_prefix=None,
        secret_scan_passed=True,
        warnings=[
            "future live SSH probe failures should persist bounded redacted stderr",
            "stdout should remain empty for connectivity-only probes",
        ],
    )


def redact_ssh_stderr(
    stderr: str,
    *,
    private_key_path: str | None = None,
    raw_ssh_key_name: str | None = None,
    host: str | None = None,
    known_hosts_path: str | None = None,
) -> LambdaSSHFailureStderrCaptureReport:
    original = stderr or ""
    redacted = original
    applied: list[str] = []
    replacements = {
        private_key_path: "<redacted-private-key-reference>",
        raw_ssh_key_name: "<redacted-ssh-key-name>",
        host: "<redacted-host>",
        known_hosts_path: "<redacted-known-hosts-path>",
    }
    for value, replacement in replacements.items():
        if value and value in redacted:
            redacted = redacted.replace(value, replacement)
            applied.append(replacement.strip("<>"))
    for index, pattern in enumerate(_SECRET_PATTERNS, start=1):
        if pattern.search(redacted):
            redacted = pattern.sub("<redacted-secret>", redacted)
            applied.append(f"secret_pattern_{index}")
    lines = redacted.splitlines()
    truncated = False
    if len(lines) > MAX_STDERR_LINES:
        lines = lines[:MAX_STDERR_LINES]
        truncated = True
    redacted = "\n".join(lines)
    encoded = redacted.encode("utf-8")
    if len(encoded) > MAX_STDERR_BYTES:
        redacted = encoded[:MAX_STDERR_BYTES].decode("utf-8", errors="ignore")
        truncated = True
    blockers: list[str] = []
    if _contains_secret_marker(redacted):
        blockers.append("redacted_stderr_contains_secret_marker")
    return LambdaSSHFailureStderrCaptureReport(
        capture_policy_status="policy_defined" if not blockers else "blocked",
        stderr_redacted=redacted,
        stderr_sha256_prefix=hashlib.sha256(original.encode("utf-8")).hexdigest()[:16],
        stderr_truncated=truncated,
        secret_scan_passed=not blockers,
        redaction_patterns_applied=sorted(set(applied)),
        blockers=blockers,
    )


def _contains_secret_marker(value: str) -> bool:
    return any(pattern.search(value) for pattern in _SECRET_PATTERNS)


def load_lambda_ssh_stderr_capture_policy(
    path: str | Path,
) -> LambdaSSHFailureStderrCaptureReport:
    return LambdaSSHFailureStderrCaptureReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_ssh_stderr_capture_policy(
    path: str | Path,
    report: LambdaSSHFailureStderrCaptureReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
