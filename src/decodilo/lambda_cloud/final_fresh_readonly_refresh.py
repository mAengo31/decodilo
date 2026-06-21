"""M028 final fresh read-only Lambda refresh report."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.live_discovery_report import (
    LambdaLiveDiscoveryReport,
    load_lambda_live_discovery_report,
)

LambdaFinalRefreshStatus = Literal[
    "not_run_no_env",
    "not_run_missing_key",
    "run_read_only_passed",
    "run_read_only_failed",
]


class LambdaFinalFreshReadOnlyRefreshPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    env_file_required_if_running: bool = True
    env_key: str = "LAMBDA_API_KEY"
    require_get_only: bool = True
    require_required_endpoint_success: bool = True
    max_refresh_attempts: int = 1
    launch_ready: bool = False
    launch_allowed: bool = False


class LambdaFinalFreshReadOnlyRefreshReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    report_id: str = "lambda-final-fresh-readonly-refresh-m028"
    refresh_status: LambdaFinalRefreshStatus
    env_file_basename: str | None = None
    env_key: str | None = None
    live_api_used: bool = False
    read_only_mode: bool = True
    all_requests_get: bool = True
    required_endpoint_success: bool | None = None
    endpoint_count_attempted: int = 0
    endpoint_count_succeeded: int = 0
    endpoint_count_unsupported_optional: int = 0
    read_operations: int = 0
    mutating_operations: int = 0
    billable_action_performed: bool = False
    secret_redacted: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    real_mutation_enabled: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> LambdaFinalFreshReadOnlyRefreshReport:
        if self.real_mutation_enabled or self.launch_ready or self.launch_allowed:
            raise ValueError("M028 refresh report cannot enable launch or mutation")
        if self.mutating_operations:
            raise ValueError("M028 refresh report cannot include mutating operations")
        if self.billable_action_performed:
            raise ValueError("M028 refresh report cannot include billable action")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_refresh_not_run_report(
    *,
    status: LambdaFinalRefreshStatus,
    env_file_basename: str | None = None,
    env_key: str = "LAMBDA_API_KEY",
    warning: str | None = None,
) -> LambdaFinalFreshReadOnlyRefreshReport:
    if status not in {"not_run_no_env", "not_run_missing_key"}:
        raise ValueError("not-run refresh helper requires a not-run status")
    return LambdaFinalFreshReadOnlyRefreshReport(
        refresh_status=status,
        env_file_basename=env_file_basename,
        env_key=_redacted_env_key_ref(env_key),
        warnings=[] if warning is None else [warning],
    )


def build_lambda_refresh_report_from_discovery(
    discovery: str | Path | LambdaLiveDiscoveryReport,
    *,
    env_file_basename: str | None = None,
    env_key: str | None = None,
) -> LambdaFinalFreshReadOnlyRefreshReport:
    report = (
        discovery
        if isinstance(discovery, LambdaLiveDiscoveryReport)
        else load_lambda_live_discovery_report(discovery)
    )
    blockers: list[str] = []
    if not report.read_only_mode:
        blockers.append("live discovery was not read-only")
    if any(entry.method != "GET" for entry in report.audit_log):
        blockers.append("non-GET request observed")
    if report.summary.mutating_operations:
        blockers.append("mutating operation observed")
    if report.billable_action_performed:
        blockers.append("billable action observed")
    if not report.required_endpoint_success:
        blockers.append("required read-only endpoint failed")
    if not report.secret_redacted:
        blockers.append("secret redaction failed")
    return LambdaFinalFreshReadOnlyRefreshReport(
        refresh_status="run_read_only_passed" if not blockers else "run_read_only_failed",
        env_file_basename=env_file_basename or report.env_file_basename,
        env_key=_redacted_env_key_ref(env_key or report.env_key),
        live_api_used=report.live_api_used,
        read_only_mode=report.read_only_mode,
        all_requests_get=not any(entry.method != "GET" for entry in report.audit_log),
        required_endpoint_success=report.required_endpoint_success,
        endpoint_count_attempted=report.endpoint_count_attempted,
        endpoint_count_succeeded=report.endpoint_count_succeeded,
        endpoint_count_unsupported_optional=report.endpoint_count_unsupported_optional,
        read_operations=len(report.audit_log),
        mutating_operations=report.summary.mutating_operations,
        billable_action_performed=report.billable_action_performed,
        secret_redacted=report.secret_redacted,
        blockers=blockers,
        warnings=[
            "M028 fresh refresh is read-only evidence only; launch remains disabled.",
            *report.warnings,
        ],
    )


def _redacted_env_key_ref(env_key: str | None) -> str | None:
    if not env_key:
        return None
    return "redacted-env-key-name"


def load_lambda_final_fresh_readonly_refresh_report(
    path: str | Path,
) -> LambdaFinalFreshReadOnlyRefreshReport:
    return LambdaFinalFreshReadOnlyRefreshReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_final_fresh_readonly_refresh_report(
    path: str | Path,
    report: LambdaFinalFreshReadOnlyRefreshReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
