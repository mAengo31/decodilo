"""Aggregate M075T runtime-smoke closeout and M075R3 retry-prep report."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.m075r3_runtime_smoke_retry_authorization import (
    load_lambda_m075r3_runtime_smoke_retry_authorization,
)
from decodilo.lambda_cloud.m075r3_runtime_smoke_runbook_preview import (
    load_lambda_m075r3_runtime_smoke_runbook_preview,
)
from decodilo.lambda_cloud.runtime_smoke_artifact_body_policy import (
    load_lambda_runtime_smoke_artifact_body_policy,
)
from decodilo.lambda_cloud.runtime_smoke_attempt_closeout import (
    load_lambda_runtime_smoke_attempt_closeout,
)


class LambdaM075TReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M075T"
    report_passed: bool
    m075r2_closeout_status: str
    artifact_metadata_captured: bool
    body_or_summary_capture_required: bool
    artifact_body_policy_status: str
    m075r3_authorization_status: str
    runbook_preview_status: str
    historical_billable_action_performed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_report(self) -> LambdaM075TReport:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("M075T report must not authorize launch or spend")
        if self.report_passed and self.blockers:
            raise ValueError("passing M075T report cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m075t_report_from_paths(
    *,
    attempt_closeout: str | Path,
    artifact_body_policy: str | Path,
    authorization: str | Path,
    runbook_preview: str | Path,
) -> LambdaM075TReport:
    closeout = load_lambda_runtime_smoke_attempt_closeout(attempt_closeout)
    policy = load_lambda_runtime_smoke_artifact_body_policy(artifact_body_policy)
    auth = load_lambda_m075r3_runtime_smoke_retry_authorization(authorization)
    preview = load_lambda_m075r3_runtime_smoke_runbook_preview(runbook_preview)
    blockers: list[str] = []
    if not closeout.closeout_succeeded:
        blockers.append("m075r2_attempt_closeout_not_succeeded")
    if policy.policy_status != "policy_defined":
        blockers.extend(policy.blockers or ["artifact_body_policy_not_defined"])
    if auth.authorization_status != "authorized_for_future_m075r3_runtime_smoke_retry":
        blockers.append("m075r3_not_authorized")
    if preview.preview_status != "ready_for_future_m075r3_runtime_smoke_retry_review":
        blockers.append("m075r3_runbook_preview_not_ready")
    return LambdaM075TReport(
        report_passed=not blockers,
        m075r2_closeout_status=closeout.closeout_status,
        artifact_metadata_captured=closeout.artifact_exists,
        body_or_summary_capture_required=True,
        artifact_body_policy_status=policy.policy_status,
        m075r3_authorization_status=auth.authorization_status,
        runbook_preview_status=preview.preview_status,
        historical_billable_action_performed=closeout.historical_billable_action_performed,
        blockers=sorted(set(blockers)),
        warnings=[
            "M075T is offline; M075R3 still requires fresh discovery and supervised approval",
        ],
    )


def load_lambda_m075t_report(path: str | Path) -> LambdaM075TReport:
    return LambdaM075TReport.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_m075t_report(path: str | Path, report: LambdaM075TReport) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
