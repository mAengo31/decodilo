"""Redaction helpers for disabled Lambda mutation request plans."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

_SECRET_FIELD_PARTS = (
    "api_key",
    "authorization",
    "bearer",
    "secret",
    "token",
    "password",
    "private_key",
    "ssh_key",
    "public_key",
)
_SENSITIVE_FIELD_PARTS = ("private_ip", "filesystem", "setup_script", "user_data")


class LambdaMutationRequestRedactionReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    redacted_payload: dict[str, Any]
    redacted_fields: list[str] = Field(default_factory=list)
    rejected_fields: list[str] = Field(default_factory=list)
    contains_secret: bool = False
    setup_script_present: bool = False
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    launch_allowed: bool = False

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def redact_lambda_mutation_request_payload(
    payload: dict[str, Any],
    *,
    reject_setup_script: bool = True,
) -> LambdaMutationRequestRedactionReport:
    redacted: dict[str, Any] = {}
    redacted_fields: list[str] = []
    rejected_fields: list[str] = []
    errors: list[str] = []
    contains_secret = False
    setup_script = False
    for key, value in payload.items():
        lowered = key.lower()
        if any(part in lowered for part in _SECRET_FIELD_PARTS):
            redacted[key] = "<redacted>"
            redacted_fields.append(key)
            contains_secret = True
            continue
        if "setup_script" in lowered or "user_data" in lowered:
            setup_script = True
            redacted[key] = "<redacted>"
            redacted_fields.append(key)
            if reject_setup_script:
                rejected_fields.append(key)
                errors.append(f"setup/user-data field is not allowed in M024: {key}")
            continue
        if any(part in lowered for part in _SENSITIVE_FIELD_PARTS):
            redacted[key] = "<redacted>"
            redacted_fields.append(key)
            continue
        redacted[key] = _redact_nested(value)
    return LambdaMutationRequestRedactionReport(
        redacted_payload=redacted,
        redacted_fields=redacted_fields,
        rejected_fields=rejected_fields,
        contains_secret=contains_secret,
        setup_script_present=setup_script,
        warnings=["Mutation request payload is a review-only summary."],
        errors=errors,
    )


def _redact_nested(value: Any) -> Any:
    if isinstance(value, dict):
        return redact_lambda_mutation_request_payload(value).redacted_payload
    if isinstance(value, list):
        return [_redact_nested(item) for item in value]
    if isinstance(value, str) and _looks_secret_like(value):
        return "<redacted>"
    return value


def _looks_secret_like(value: str) -> bool:
    lowered = value.lower()
    return (
        "authorization:" in lowered
        or lowered.startswith("bearer ")
        or lowered.startswith("lambda_")
        or (len(value) > 40 and any(ch.isdigit() for ch in value))
    )
