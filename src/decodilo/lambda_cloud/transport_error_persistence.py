"""Persisted Lambda mutation transport error evidence."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.launch_transport_error_taxonomy import (
    LambdaLaunchTransportErrorTaxonomyReport,
    classify_lambda_launch_transport_error,
)
from decodilo.lambda_cloud.live_discovery_redaction import (
    redact_lambda_text,
    scan_lambda_secret_leaks,
)
from decodilo.lambda_cloud.mutation_transport_diagnostics import (
    LambdaMutationTransportDiagnostics,
)
from decodilo.lambda_cloud.real_launch_result import redact_instance_id


class LambdaTransportErrorPersistenceRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    request_attempt_id: str
    operation: str
    request_sent: bool
    status_code: int | None = None
    reason: str | None = None
    content_type: str | None = None
    content_length: int | None = None
    body_size_bytes: int | None = None
    response_classification: str = "unknown"
    exception_type: str
    exception_message_redacted: str
    provider_error_message_redacted: str | None = None
    elapsed_seconds: float
    owned_instance_id_redacted: str | None = None
    manual_review_required: bool = True
    no_auto_retry: bool = True
    secret_scan_passed: bool = True
    taxonomy: LambdaLaunchTransportErrorTaxonomyReport
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False

    @model_validator(mode="after")
    def _validate_disabled_and_redacted(self) -> LambdaTransportErrorPersistenceRecord:
        if self.launch_ready or self.launch_allowed:
            raise ValueError("transport error persistence cannot enable launch")
        if not self.no_auto_retry:
            raise ValueError("transport error persistence must preserve no-auto-retry")
        if not self.secret_scan_passed:
            raise ValueError("transport error persistence contains secret-like data")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_transport_error_persistence_record(
    *,
    operation: str,
    request_sent: bool,
    exception: BaseException,
    elapsed_seconds: float,
    diagnostics: Sequence[LambdaMutationTransportDiagnostics] | None = None,
    owned_instance_id: str | None = None,
) -> LambdaTransportErrorPersistenceRecord:
    capture = _latest_capture(operation, diagnostics or [])
    metadata = capture.response_capture.metadata if capture and capture.response_capture else None
    status_code = metadata.status_code if metadata else None
    response_classification = (
        capture.response_capture.classification
        if capture and capture.response_capture
        else "unknown"
    )
    exception_type = type(exception).__name__
    message = redact_lambda_text(str(exception))
    taxonomy = classify_lambda_launch_transport_error(
        status_code=status_code,
        response_classification=response_classification,
        exception_type=exception_type,
    )
    secret_leaks = scan_lambda_secret_leaks(
        json.dumps(
            {
                "reason": None if metadata is None else metadata.reason,
                "content_type": None if metadata is None else metadata.content_type,
                "exception_type": exception_type,
                "exception_message": message,
                "provider_error_message": None
                if metadata is None
                else metadata.provider_error_message_redacted,
            },
            sort_keys=True,
        )
    )
    return LambdaTransportErrorPersistenceRecord(
        request_attempt_id=_attempt_id(operation, elapsed_seconds, exception_type),
        operation=operation,
        request_sent=request_sent,
        status_code=status_code,
        reason=None if metadata is None else metadata.reason,
        content_type=None if metadata is None else metadata.content_type,
        content_length=None if metadata is None else metadata.content_length,
        body_size_bytes=None if metadata is None else metadata.body_size_bytes,
        response_classification=response_classification,
        exception_type=exception_type,
        exception_message_redacted=message,
        provider_error_message_redacted=None
        if metadata is None
        else metadata.provider_error_message_redacted,
        elapsed_seconds=elapsed_seconds,
        owned_instance_id_redacted=redact_instance_id(owned_instance_id),
        secret_scan_passed=not secret_leaks,
        taxonomy=taxonomy,
        warnings=[
            "mutation transport error persisted before process exit",
            "automatic launch retry remains forbidden",
        ],
        errors=[message],
    )


def load_lambda_transport_error_persistence_record(
    path: str | Path,
) -> LambdaTransportErrorPersistenceRecord:
    return LambdaTransportErrorPersistenceRecord.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_transport_error_persistence_record(
    path: str | Path,
    record: LambdaTransportErrorPersistenceRecord,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(record.to_json(), encoding="utf-8")


def _latest_capture(
    operation: str,
    diagnostics: Sequence[LambdaMutationTransportDiagnostics],
) -> LambdaMutationTransportDiagnostics | None:
    for item in reversed(list(diagnostics)):
        if item.operation == operation and item.response_capture is not None:
            return item
    return None


def _attempt_id(operation: str, elapsed_seconds: float, exception_type: str) -> str:
    digest = hashlib.sha256(
        f"{operation}:{elapsed_seconds:.9f}:{exception_type}".encode()
    ).hexdigest()
    return f"lambda-transport-error-{digest[:16]}"
