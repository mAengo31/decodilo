"""Endpoint calibration records for Lambda live read-only discovery."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.endpoint_policy import endpoint_for_operation
from decodilo.lambda_cloud.live_discovery_redaction import redact_lambda_text
from decodilo.lambda_cloud.live_response_shapes import (
    collect_lambda_unknown_fields,
    summarize_lambda_response_shape,
)
from decodilo.lambda_cloud.read_only_audit import LambdaReadOnlyAuditEntry

LambdaEndpointClassification = Literal[
    "required_standard_endpoint",
    "optional_standard_endpoint",
    "unsupported_optional_endpoint",
    "schema_validation_failure",
    "auth_failure",
    "rate_limit_failure",
    "server_failure",
    "endpoint_policy_denied",
    "mutation_denied",
]

REQUIRED_STANDARD_OPERATIONS: frozenset[str] = frozenset(
    {"list_instance_types", "list_instances"}
)
OPTIONAL_STANDARD_OPERATIONS: frozenset[str] = frozenset(
    {
        "list_regions",
        "list_images",
        "list_ssh_keys",
        "list_filesystems",
        "get_quota",
        "get_usage_estimate",
    }
)


class LambdaEndpointResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    operation: str
    method: str = "GET"
    endpoint_path_template: str
    endpoint_path_used: str
    allowed_by_endpoint_policy: bool
    allowed_by_mutation_guard: bool
    attempted: bool = True
    success: bool
    status_code: int | None = None
    response_shape_summary: str | None = None
    item_count: int | None = None
    pagination_observed: bool = False
    unknown_fields_seen: list[str] = Field(default_factory=list)
    error_type: str | None = None
    error_message_redacted: str | None = None
    live_api_used: bool
    mutation: bool = False
    billable_action_performed: bool = False
    endpoint_classification: LambdaEndpointClassification = "optional_standard_endpoint"


class LambdaEndpointCalibrationReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    endpoint_results: list[LambdaEndpointResult] = Field(default_factory=list)
    endpoint_count_attempted: int = 0
    endpoint_count_succeeded: int = 0
    endpoint_count_failed: int = 0
    endpoint_count_failed_required: int = 0
    endpoint_count_failed_optional: int = 0
    endpoint_count_unsupported_optional: int = 0
    required_endpoint_success: bool = True
    optional_endpoint_warnings: list[str] = Field(default_factory=list)
    read_operations: int = 0
    mutating_operations: int = 0
    billable_action_performed: bool = False
    live_api_used: bool = False
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def endpoint_result_for_success(
    *,
    operation: str,
    payload: Any,
    audit_entry: LambdaReadOnlyAuditEntry | None,
    live_api_used: bool,
) -> LambdaEndpointResult:
    endpoint = _endpoint_template(operation)
    shape = summarize_lambda_response_shape(payload)
    return LambdaEndpointResult(
        operation=operation,
        endpoint_path_template=endpoint,
        endpoint_path_used=audit_entry.endpoint if audit_entry is not None else endpoint,
        allowed_by_endpoint_policy=True,
        allowed_by_mutation_guard=True,
        success=True,
        status_code=None if audit_entry is None else audit_entry.status_code,
        response_shape_summary=shape.compact,
        item_count=shape.item_count,
        pagination_observed=shape.pagination_observed,
        unknown_fields_seen=collect_lambda_unknown_fields(payload),
        live_api_used=live_api_used,
        endpoint_classification=_success_classification(operation),
    )


def endpoint_result_for_failure(
    *,
    operation: str,
    exc: Exception,
    audit_entry: LambdaReadOnlyAuditEntry | None,
    live_api_used: bool,
) -> LambdaEndpointResult:
    endpoint = _endpoint_template(operation)
    return LambdaEndpointResult(
        operation=operation,
        endpoint_path_template=endpoint,
        endpoint_path_used=audit_entry.endpoint if audit_entry is not None else endpoint,
        allowed_by_endpoint_policy=True,
        allowed_by_mutation_guard=True,
        success=False,
        status_code=None if audit_entry is None else audit_entry.status_code,
        error_type=exc.__class__.__name__,
        error_message_redacted=redact_lambda_text(str(exc)),
        live_api_used=live_api_used,
        endpoint_classification=_failure_classification(
            operation,
            exc=exc,
            status_code=None if audit_entry is None else audit_entry.status_code,
        ),
    )


def build_lambda_endpoint_calibration_report(
    results: list[LambdaEndpointResult],
    *,
    warnings: list[str] | None = None,
    errors: list[str] | None = None,
) -> LambdaEndpointCalibrationReport:
    failed_required = [
        result
        for result in results
        if result.attempted and not result.success and _is_required(result.operation)
    ]
    failed_optional = [
        result
        for result in results
        if result.attempted and not result.success and not _is_required(result.operation)
    ]
    unsupported_optional = [
        result
        for result in failed_optional
        if result.endpoint_classification == "unsupported_optional_endpoint"
    ]
    return LambdaEndpointCalibrationReport(
        endpoint_results=results,
        endpoint_count_attempted=sum(1 for result in results if result.attempted),
        endpoint_count_succeeded=sum(1 for result in results if result.success),
        endpoint_count_failed=sum(
            1 for result in results if result.attempted and not result.success
        ),
        endpoint_count_failed_required=len(failed_required),
        endpoint_count_failed_optional=len(failed_optional),
        endpoint_count_unsupported_optional=len(unsupported_optional),
        required_endpoint_success=not failed_required,
        optional_endpoint_warnings=[
            f"{result.operation}: {result.endpoint_classification}"
            for result in failed_optional
        ],
        read_operations=sum(1 for result in results if result.method.upper() == "GET"),
        mutating_operations=sum(1 for result in results if result.mutation),
        billable_action_performed=any(result.billable_action_performed for result in results),
        live_api_used=any(result.live_api_used for result in results),
        warnings=list(warnings or []),
        errors=list(errors or []),
    )


def load_lambda_endpoint_calibration_report(path: str | Path) -> LambdaEndpointCalibrationReport:
    return LambdaEndpointCalibrationReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_endpoint_calibration_report(
    path: str | Path,
    report: LambdaEndpointCalibrationReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")


def _endpoint_template(operation: str) -> str:
    try:
        if operation == "get_instance":
            return "/instances/{instance_id}"
        return endpoint_for_operation(operation).path
    except Exception:  # noqa: BLE001
        return "<unknown>"


def _success_classification(operation: str) -> LambdaEndpointClassification:
    if _is_required(operation):
        return "required_standard_endpoint"
    return "optional_standard_endpoint"


def _failure_classification(
    operation: str,
    *,
    exc: Exception,
    status_code: int | None,
) -> LambdaEndpointClassification:
    error_type = exc.__class__.__name__
    if status_code == 404 and not _is_required(operation):
        return "unsupported_optional_endpoint"
    if "ValidationError" in error_type:
        return "schema_validation_failure"
    if error_type == "LambdaAuthError":
        return "auth_failure"
    if error_type == "LambdaRateLimitError":
        return "rate_limit_failure"
    if error_type == "LambdaServerError":
        return "server_failure"
    if error_type == "LambdaMutationForbiddenError":
        return "mutation_denied"
    return "endpoint_policy_denied"


def _is_required(operation: str) -> bool:
    return operation in REQUIRED_STANDARD_OPERATIONS
