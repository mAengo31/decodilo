"""Capture policy for future Lambda launch responses."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LambdaLaunchResponseCapturePolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    capture_http_status: bool = True
    capture_response_content_type: bool = True
    capture_response_body_size: bool = True
    capture_redacted_response_headers: bool = True
    capture_raw_response_body: bool = False
    capture_raw_authorization_header: bool = False
    capture_secret_values: bool = False
    capture_parse_failure_reason: bool = True
    capture_transport_exception_type: bool = True
    policy_passed: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False

    @model_validator(mode="before")
    @classmethod
    def _derive_policy_status(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        blockers = list(data.get("blockers") or [])
        if data.get("capture_raw_response_body", False):
            blockers.append("raw response body capture is forbidden")
        if data.get("capture_raw_authorization_header", False):
            blockers.append("raw Authorization header capture is forbidden")
        if data.get("capture_secret_values", False):
            blockers.append("secret value capture is forbidden")
        if blockers:
            data = {**data, "policy_passed": False, "blockers": blockers}
        return data

    @model_validator(mode="after")
    def _validate_safe_capture(self) -> LambdaLaunchResponseCapturePolicy:
        if self.launch_ready or self.launch_allowed:
            raise ValueError("response capture policy cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_launch_response_capture_policy() -> LambdaLaunchResponseCapturePolicy:
    return LambdaLaunchResponseCapturePolicy(
        warnings=["future launches must capture status and redacted metadata before parsing"]
    )


def load_lambda_launch_response_capture_policy(
    path: str | Path,
) -> LambdaLaunchResponseCapturePolicy:
    return LambdaLaunchResponseCapturePolicy.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_launch_response_capture_policy(
    path: str | Path,
    policy: LambdaLaunchResponseCapturePolicy,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(policy.to_json(), encoding="utf-8")
