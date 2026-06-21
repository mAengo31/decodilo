"""Review-only lock for M033 response-capture settings."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LambdaResponseCaptureSettingsLock(BaseModel):
    model_config = ConfigDict(frozen=True)

    lock_id: str = "lambda-m033-response-capture-settings-lock"
    capture_http_status_before_parse: bool = True
    capture_redacted_headers: bool = True
    capture_content_type: bool = True
    capture_content_length: bool = True
    capture_body_size: bool = True
    distinguish_timeout: bool = True
    distinguish_malformed_json: bool = True
    distinguish_non_json_body: bool = True
    distinguish_empty_body: bool = True
    body_sample_enabled: bool = False
    max_body_sample_bytes: int | None = None
    secret_redaction_enabled: bool = True
    lock_hash: str = ""
    lock_passed: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False

    @model_validator(mode="after")
    def _validate_lock(self) -> LambdaResponseCaptureSettingsLock:
        if self.launch_ready or self.launch_allowed:
            raise ValueError("response-capture settings lock cannot enable launch")
        blockers = _lock_blockers(self)
        if self.lock_passed and blockers:
            raise ValueError("response-capture lock cannot pass with blockers")
        if self.body_sample_enabled and self.max_body_sample_bytes is None:
            raise ValueError("body sample requires max_body_sample_bytes")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_response_capture_settings_lock(
    *,
    capture_http_status_before_parse: bool = True,
    capture_redacted_headers: bool = True,
    capture_content_type: bool = True,
    capture_content_length: bool = True,
    capture_body_size: bool = True,
    distinguish_timeout: bool = True,
    distinguish_malformed_json: bool = True,
    distinguish_non_json_body: bool = True,
    distinguish_empty_body: bool = True,
    body_sample_enabled: bool = False,
    max_body_sample_bytes: int | None = None,
    secret_redaction_enabled: bool = True,
) -> LambdaResponseCaptureSettingsLock:
    payload = {
        "capture_http_status_before_parse": capture_http_status_before_parse,
        "capture_redacted_headers": capture_redacted_headers,
        "capture_content_type": capture_content_type,
        "capture_content_length": capture_content_length,
        "capture_body_size": capture_body_size,
        "distinguish_timeout": distinguish_timeout,
        "distinguish_malformed_json": distinguish_malformed_json,
        "distinguish_non_json_body": distinguish_non_json_body,
        "distinguish_empty_body": distinguish_empty_body,
        "body_sample_enabled": body_sample_enabled,
        "max_body_sample_bytes": max_body_sample_bytes,
        "secret_redaction_enabled": secret_redaction_enabled,
    }
    provisional = LambdaResponseCaptureSettingsLock(
        **payload,
        lock_passed=False,
        blockers=[],
    )
    blockers = _lock_blockers(provisional)
    warnings = (
        ["body sample enabled; ensure redaction remains active"]
        if body_sample_enabled
        else ["body sample disabled by default"]
    )
    return LambdaResponseCaptureSettingsLock(
        **payload,
        lock_hash=hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode("utf-8")
        ).hexdigest(),
        lock_passed=not blockers,
        blockers=blockers,
        warnings=warnings,
    )


def _lock_blockers(lock: LambdaResponseCaptureSettingsLock) -> list[str]:
    blockers: list[str] = []
    required = {
        "capture_http_status_before_parse": lock.capture_http_status_before_parse,
        "capture_redacted_headers": lock.capture_redacted_headers,
        "capture_content_type": lock.capture_content_type,
        "capture_content_length": lock.capture_content_length,
        "capture_body_size": lock.capture_body_size,
        "distinguish_timeout": lock.distinguish_timeout,
        "distinguish_malformed_json": lock.distinguish_malformed_json,
        "distinguish_non_json_body": lock.distinguish_non_json_body,
        "distinguish_empty_body": lock.distinguish_empty_body,
        "secret_redaction_enabled": lock.secret_redaction_enabled,
    }
    blockers.extend(name for name, enabled in required.items() if not enabled)
    return blockers


def load_lambda_response_capture_settings_lock(
    path: str | Path,
) -> LambdaResponseCaptureSettingsLock:
    return LambdaResponseCaptureSettingsLock.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_response_capture_settings_lock(
    path: str | Path,
    lock: LambdaResponseCaptureSettingsLock,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(lock.to_json(), encoding="utf-8")
