"""Aggregate M075U update-stream failure closeout and local-fix report."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.dev.runtime_smoke import load_runtime_smoke_report
from decodilo.lambda_cloud.m075r4_runtime_smoke_retry_authorization import (
    load_lambda_m075r4_runtime_smoke_retry_authorization,
)
from decodilo.lambda_cloud.m075r4_runtime_smoke_runbook_preview import (
    load_lambda_m075r4_runtime_smoke_runbook_preview,
)
from decodilo.lambda_cloud.runtime_smoke_update_stream_closeout import (
    load_lambda_runtime_smoke_update_stream_closeout,
)
from decodilo.lambda_cloud.runtime_smoke_update_stream_diagnostic import (
    load_lambda_runtime_smoke_update_stream_diagnostic,
)
from decodilo.lambda_cloud.runtime_smoke_update_stream_failure_record import (
    load_lambda_runtime_smoke_update_stream_failure_record,
)


class LambdaM075UReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M075U"
    report_passed: bool
    m075r3_failure_status: str
    m075r3_failed_check: str | None = None
    m075r3_error_classification: str | None = None
    m075r3_safe_error: str | None = None
    closeout_status: str
    diagnostic_status: str
    local_reproduction_status: str
    local_before_runtime_smoke_status: str
    local_before_error_classification: str | None = None
    local_after_runtime_smoke_status: str
    local_after_error_classification: str | None = None
    runtime_smoke_now_passes_locally: bool
    code_fix_summary: str
    m075r4_authorization_status: str
    runbook_preview_status: str
    historical_billable_action_performed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_report(self) -> LambdaM075UReport:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("M075U report must not authorize launch or spend")
        if self.report_passed and self.blockers:
            raise ValueError("passing M075U report cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m075u_report_from_paths(
    *,
    failure_record: str | Path,
    closeout: str | Path,
    diagnostic: str | Path,
    local_before_report: str | Path,
    local_after_report: str | Path,
    authorization: str | Path,
    runbook_preview: str | Path,
) -> LambdaM075UReport:
    record = load_lambda_runtime_smoke_update_stream_failure_record(failure_record)
    closeout_obj = load_lambda_runtime_smoke_update_stream_closeout(closeout)
    diag = load_lambda_runtime_smoke_update_stream_diagnostic(diagnostic)
    before = load_runtime_smoke_report(local_before_report)
    after = load_runtime_smoke_report(local_after_report)
    auth = load_lambda_m075r4_runtime_smoke_retry_authorization(authorization)
    preview = load_lambda_m075r4_runtime_smoke_runbook_preview(runbook_preview)
    blockers: list[str] = []
    if record.failure_status != "runtime_smoke_update_stream_failed":
        blockers.append("m075r3_update_stream_failure_not_classified")
    if not closeout_obj.closeout_succeeded:
        blockers.append("m075r3_update_stream_closeout_not_succeeded")
    if diag.diagnostic_status != "diagnosed_update_stream_timeout_path":
        blockers.append("update_stream_diagnostic_not_passed")
    if after.runtime_smoke_status != "passed":
        blockers.append("runtime_smoke_after_fix_not_passed")
    if after.protocol_or_event_check_passed is not True:
        blockers.append("protocol_or_event_check_after_fix_not_passed")
    if auth.authorization_status != "authorized_for_future_m075r4_runtime_smoke_retry":
        blockers.append("m075r4_not_authorized")
    if preview.preview_status != "ready_for_future_m075r4_runtime_smoke_retry_review":
        blockers.append("m075r4_runbook_preview_not_ready")
    return LambdaM075UReport(
        report_passed=not blockers,
        m075r3_failure_status=record.failure_status,
        m075r3_failed_check=record.failed_check,
        m075r3_error_classification=record.error_classification,
        m075r3_safe_error=record.safe_error,
        closeout_status=closeout_obj.closeout_status,
        diagnostic_status=diag.diagnostic_status,
        local_reproduction_status=diag.local_reproduction_status,
        local_before_runtime_smoke_status=before.runtime_smoke_status,
        local_before_error_classification=before.error_classification,
        local_after_runtime_smoke_status=after.runtime_smoke_status,
        local_after_error_classification=after.error_classification,
        runtime_smoke_now_passes_locally=after.runtime_smoke_status == "passed",
        code_fix_summary=(
            "UpdateStream now tracks committed global version and catches asyncio "
            "timeouts; runtime-smoke now validates a deterministic committed synthetic "
            "update stream instead of relying on a 1 ms timeout probe."
        ),
        m075r4_authorization_status=auth.authorization_status,
        runbook_preview_status=preview.preview_status,
        historical_billable_action_performed=record.historical_billable_action_performed,
        blockers=sorted(set(blockers)),
        warnings=[
            "M075U is offline and non-billable",
            "M075R4 authorization remains future-only",
        ],
    )


def load_lambda_m075u_report(path: str | Path) -> LambdaM075UReport:
    return LambdaM075UReport.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_m075u_report(path: str | Path, report: LambdaM075UReport) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
