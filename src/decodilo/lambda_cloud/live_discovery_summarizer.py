"""Public and local summaries for Lambda live discovery reports."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from decodilo.lambda_cloud.live_discovery_redaction import (
    LambdaLiveDiscoveryRedactionPolicy,
    LambdaRedactionMode,
    redact_lambda_identifier,
    redact_lambda_payload,
)
from decodilo.lambda_cloud.live_discovery_report import LambdaLiveDiscoveryReport


class LambdaLiveDiscoverySafeSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    redaction_mode: LambdaRedactionMode
    source: str
    live_api_used: bool
    read_only_mode: bool
    endpoint_count_attempted: int
    endpoint_count_succeeded: int
    endpoint_count_failed: int
    endpoint_count_failed_required: int = 0
    endpoint_count_failed_optional: int = 0
    endpoint_count_unsupported_optional: int = 0
    required_endpoint_success: bool = True
    optional_endpoint_warnings: list[str] = Field(default_factory=list)
    read_operations: int
    mutating_operations: int
    billable_action_performed: bool
    region_count: int
    instance_type_count: int
    instance_count: int
    unmanaged_count: int
    unmanaged_instances: list[str] = Field(default_factory=list)
    manual_review_required: bool = False
    audit_status: str | None = None
    secret_source: str | None = None
    secret_loaded: bool = False
    env_file_basename: str | None = None
    env_key: str | None = None
    launch_ready: bool = False
    launch_allowed: bool = False
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def summarize_lambda_live_discovery(
    report: LambdaLiveDiscoveryReport,
    *,
    redaction_mode: LambdaRedactionMode = "public_summary",
) -> LambdaLiveDiscoverySafeSummary:
    policy = LambdaLiveDiscoveryRedactionPolicy(mode=redaction_mode)
    if redaction_mode == "public_summary":
        unmanaged = [
            redact_lambda_identifier(instance_id) for instance_id in report.unmanaged_instances
        ]
    else:
        unmanaged = redact_lambda_payload(report.unmanaged_instances, policy=policy)
    return LambdaLiveDiscoverySafeSummary(
        redaction_mode=redaction_mode,
        source=report.source,
        live_api_used=report.live_api_used,
        read_only_mode=report.read_only_mode,
        endpoint_count_attempted=report.endpoint_count_attempted,
        endpoint_count_succeeded=report.endpoint_count_succeeded,
        endpoint_count_failed=report.endpoint_count_failed,
        endpoint_count_failed_required=report.endpoint_count_failed_required,
        endpoint_count_failed_optional=report.endpoint_count_failed_optional,
        endpoint_count_unsupported_optional=report.endpoint_count_unsupported_optional,
        required_endpoint_success=report.required_endpoint_success,
        optional_endpoint_warnings=report.optional_endpoint_warnings,
        read_operations=report.summary.read_operations,
        mutating_operations=report.summary.mutating_operations,
        billable_action_performed=report.billable_action_performed,
        region_count=len(report.regions),
        instance_type_count=len(report.instance_types),
        instance_count=len(report.instances),
        unmanaged_count=len(report.unmanaged_instances),
        unmanaged_instances=unmanaged,
        manual_review_required=bool(report.unmanaged_instances),
        secret_source=report.secret_source,
        secret_loaded=report.secret_loaded,
        env_file_basename=report.env_file_basename,
        env_key=_redacted_env_key_ref(report.env_key),
        launch_ready=report.launch_ready,
        launch_allowed=report.launch_allowed,
        warnings=_redact_env_key_refs(report.warnings, env_key=report.env_key),
        errors=report.errors,
    )


def _redacted_env_key_ref(env_key: str | None) -> str | None:
    if not env_key:
        return None
    return "redacted-env-key-name"


def _redact_env_key_refs(values: list[str], *, env_key: str | None) -> list[str]:
    redacted: list[str] = []
    for value in values:
        cleaned = value
        if env_key:
            cleaned = cleaned.replace(env_key, "redacted-env-key-name")
        cleaned = cleaned.replace("LAMBDA_API_KEY", "redacted-env-key-name")
        redacted.append(cleaned)
    return redacted


def write_lambda_live_discovery_summary(
    path: str | Path,
    summary: LambdaLiveDiscoverySafeSummary,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(summary.to_json(), encoding="utf-8")
