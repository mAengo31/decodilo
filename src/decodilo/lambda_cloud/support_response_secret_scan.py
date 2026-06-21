"""Secret scan for M037 support/operator response artifacts."""

from __future__ import annotations

import json
import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

SECRET_PATTERNS = {
    "authorization_header": re.compile(r"Authorization\s*:", re.IGNORECASE),
    "bearer_token": re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]+", re.IGNORECASE),
    "lambda_api_key": re.compile(r"LAMBDA_API_KEY", re.IGNORECASE),
    "api_key_value": re.compile(r"api[_-]?key\s*[:=]\s*[A-Za-z0-9._~+/=-]+", re.IGNORECASE),
    "private_key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----", re.IGNORECASE),
    "password_value": re.compile(r"password\s*[:=]\s*\\?\"?[^\s,}\"']+", re.IGNORECASE),
}


class LambdaSupportResponseSecretScanReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    scanned_ref: str | None = None
    scan_passed: bool
    findings: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaSupportResponseSecretScanReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("support response secret scan cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def scan_lambda_support_response_text(
    text: str,
    *,
    scanned_ref: str | None = None,
) -> LambdaSupportResponseSecretScanReport:
    findings = [
        name for name, pattern in SECRET_PATTERNS.items() if pattern.search(text)
    ]
    return LambdaSupportResponseSecretScanReport(
        scanned_ref=scanned_ref,
        scan_passed=not findings,
        findings=findings,
        blockers=[f"secret_like_value_detected:{item}" for item in findings],
    )


def scan_lambda_support_response_path(
    path: str | Path,
) -> LambdaSupportResponseSecretScanReport:
    target = Path(path)
    if not target.exists():
        return LambdaSupportResponseSecretScanReport(
            scanned_ref=str(target),
            scan_passed=False,
            blockers=["support_response_missing"],
        )
    return scan_lambda_support_response_text(
        target.read_text(encoding="utf-8"),
        scanned_ref=str(target),
    )


def load_lambda_support_response_secret_scan_report(
    path: str | Path,
) -> LambdaSupportResponseSecretScanReport:
    return LambdaSupportResponseSecretScanReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_support_response_secret_scan_report(
    path: str | Path,
    report: LambdaSupportResponseSecretScanReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
