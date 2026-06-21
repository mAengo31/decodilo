"""Safe HTTP response metadata capture for Lambda mutation diagnostics."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.live_discovery_redaction import (
    redact_lambda_text,
    scan_lambda_secret_leaks,
)

LambdaHTTPResponseClassification = Literal[
    "success_json",
    "success_empty_body",
    "success_non_json",
    "http_error_json",
    "http_error_non_json",
    "timeout",
    "connection_error",
    "malformed_json",
    "schema_validation_failure",
    "unknown",
]


class LambdaHTTPResponseCapturePolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    capture_body_sample: bool = False
    max_body_sample_bytes: int = Field(default=256, ge=0, le=2048)
    redact_authorization_header: bool = True
    launch_ready: bool = False
    launch_allowed: bool = False

    @model_validator(mode="after")
    def _disabled(self) -> LambdaHTTPResponseCapturePolicy:
        if self.launch_ready or self.launch_allowed:
            raise ValueError("HTTP response capture policy cannot enable launch")
        return self


class LambdaHTTPResponseMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    method: str
    endpoint_path_template: str
    endpoint_path_redacted: str
    status_code: int | None = None
    reason: str | None = None
    content_type: str | None = None
    content_length: int | None = None
    body_size_bytes: int | None = None
    body_sha256_prefix: str | None = None
    headers_redacted: dict[str, str] = Field(default_factory=dict)
    elapsed_seconds: float | None = None
    exception_type: str | None = None
    exception_message_redacted: str | None = None
    provider_error_message_redacted: str | None = None
    response_body_sample_redacted: str | None = None
    secret_scan_passed: bool = True
    billable_action_performed: bool | None = False
    mutation_operation_name: str
    launch_ready: bool = False
    launch_allowed: bool = False


class LambdaHTTPResponseCapture(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    metadata: LambdaHTTPResponseMetadata
    classification: LambdaHTTPResponseClassification
    json_parse_attempted: bool = False
    json_parse_succeeded: bool = False
    schema_validation_failed: bool = False
    status_captured_before_parse: bool = True
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False

    @model_validator(mode="after")
    def _validate_flags(self) -> LambdaHTTPResponseCapture:
        if self.launch_ready or self.launch_allowed:
            raise ValueError("HTTP response capture cannot enable launch")
        if not self.metadata.secret_scan_passed:
            raise ValueError("HTTP response capture contains secret-like data")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def capture_lambda_http_response(
    *,
    method: str,
    endpoint_path_template: str,
    endpoint_path: str,
    mutation_operation_name: str,
    status_code: int | None = None,
    reason: str | None = None,
    headers: dict[str, Any] | None = None,
    body: bytes | str | None = None,
    elapsed_seconds: float | None = None,
    exception: BaseException | None = None,
    exception_type: str | None = None,
    exception_message: str | None = None,
    schema_validation_failed: bool = False,
    billable_action_performed: bool | None = False,
    policy: LambdaHTTPResponseCapturePolicy | None = None,
) -> LambdaHTTPResponseCapture:
    policy = policy or LambdaHTTPResponseCapturePolicy()
    body_bytes = _body_bytes(body)
    redacted_headers = _redact_headers(headers or {})
    content_type = _content_type(redacted_headers)
    content_length = _content_length(redacted_headers)
    parsed_json = _parse_json(body_bytes)
    parse_attempted = bool(body_bytes) and _looks_json(content_type, body_bytes)
    parse_succeeded = parsed_json is not None
    provider_error_message = _provider_error_message(parsed_json, status_code=status_code)
    exception_name = exception_type or (type(exception).__name__ if exception else None)
    exception_text = exception_message or (str(exception) if exception else None)
    classification = _classify(
        status_code=status_code,
        content_type=content_type,
        body=body_bytes,
        exception_type=exception_name,
        json_parse_attempted=parse_attempted,
        json_parse_succeeded=parse_succeeded,
        schema_validation_failed=schema_validation_failed,
    )
    sample = _body_sample(body_bytes, policy=policy)
    metadata = LambdaHTTPResponseMetadata(
        method=method.upper(),
        endpoint_path_template=endpoint_path_template,
        endpoint_path_redacted=_redact_path(endpoint_path),
        status_code=status_code,
        reason=reason,
        content_type=content_type,
        content_length=content_length,
        body_size_bytes=None if body_bytes is None else len(body_bytes),
        body_sha256_prefix=_sha_prefix(body_bytes),
        headers_redacted=redacted_headers,
        elapsed_seconds=elapsed_seconds,
        exception_type=exception_name,
        exception_message_redacted=None
        if exception_text is None
        else redact_lambda_text(exception_text),
        provider_error_message_redacted=provider_error_message,
        response_body_sample_redacted=sample,
        secret_scan_passed=_secret_scan_passed(
            {
                "headers": redacted_headers,
                "exception": exception_text,
                "provider_error_message": provider_error_message,
                "sample": sample,
            }
        ),
        billable_action_performed=billable_action_performed,
        mutation_operation_name=mutation_operation_name,
    )
    return LambdaHTTPResponseCapture(
        metadata=metadata,
        classification=classification,
        json_parse_attempted=parse_attempted,
        json_parse_succeeded=parse_succeeded,
        schema_validation_failed=schema_validation_failed,
    )


def _classify(
    *,
    status_code: int | None,
    content_type: str | None,
    body: bytes | None,
    exception_type: str | None,
    json_parse_attempted: bool,
    json_parse_succeeded: bool,
    schema_validation_failed: bool,
) -> LambdaHTTPResponseClassification:
    lowered_exception = (exception_type or "").lower()
    if "timeout" in lowered_exception:
        return "timeout"
    if exception_type and status_code is None:
        return "connection_error"
    if schema_validation_failed:
        return "schema_validation_failure"
    if status_code is None:
        return "unknown"
    is_success = 200 <= status_code < 300
    if not body:
        return "success_empty_body" if is_success else "http_error_non_json"
    if json_parse_attempted and not json_parse_succeeded:
        return "malformed_json"
    if is_success and json_parse_succeeded:
        return "success_json"
    if is_success:
        return "success_non_json"
    if json_parse_succeeded:
        return "http_error_json"
    return "http_error_non_json"


def _body_bytes(body: bytes | str | None) -> bytes | None:
    if body is None:
        return None
    if isinstance(body, bytes):
        return body
    return body.encode("utf-8")


def _parse_json(body: bytes | None) -> Any | None:
    if not body:
        return None
    try:
        return json.loads(body.decode("utf-8"))
    except Exception:  # noqa: BLE001
        return None


def _looks_json(content_type: str | None, body: bytes | None) -> bool:
    if not body:
        return False
    stripped = body.lstrip()
    if content_type and "json" in content_type.lower():
        return True
    return stripped.startswith((b"{", b"["))


def _provider_error_message(
    parsed_json: Any | None,
    *,
    status_code: int | None,
) -> str | None:
    if status_code is None or status_code < 400 or status_code >= 500:
        return None
    if not isinstance(parsed_json, dict):
        return None
    candidate = None
    error = parsed_json.get("error")
    if isinstance(error, dict):
        candidate = error.get("message")
    elif isinstance(error, str):
        candidate = error
    if candidate is None:
        candidate = parsed_json.get("message")
    if not isinstance(candidate, str) or not candidate:
        return None
    return redact_lambda_text(candidate)


def _redact_headers(headers: dict[str, Any]) -> dict[str, str]:
    redacted: dict[str, str] = {}
    for key, value in headers.items():
        key_text = str(key)
        lowered = key_text.lower()
        if lowered in {"authorization", "cookie", "set-cookie"}:
            redacted[key_text] = "<redacted-secret>"
            continue
        redacted[key_text] = redact_lambda_text(str(value))
    return redacted


def _content_type(headers: dict[str, str]) -> str | None:
    for key, value in headers.items():
        if key.lower() == "content-type":
            return value
    return None


def _content_length(headers: dict[str, str]) -> int | None:
    for key, value in headers.items():
        if key.lower() == "content-length":
            try:
                return int(value)
            except ValueError:
                return None
    return None


def _sha_prefix(body: bytes | None) -> str | None:
    if body is None:
        return None
    return hashlib.sha256(body).hexdigest()[:12]


def _body_sample(
    body: bytes | None,
    *,
    policy: LambdaHTTPResponseCapturePolicy,
) -> str | None:
    if not body or not policy.capture_body_sample:
        return None
    sample = body[: policy.max_body_sample_bytes].decode("utf-8", errors="replace")
    return redact_lambda_text(sample)


def _redact_path(path: str) -> str:
    return redact_lambda_text(path)


def _secret_scan_passed(payload: Any) -> bool:
    return not scan_lambda_secret_leaks(payload)
