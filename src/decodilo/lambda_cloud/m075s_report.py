"""Aggregate M075S runtime-smoke failure closeout and retry-prep report."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.m075r2_runtime_smoke_retry_authorization import (
    load_lambda_m075r2_runtime_smoke_retry_authorization,
)
from decodilo.lambda_cloud.m075r2_runtime_smoke_runbook_preview import (
    load_lambda_m075r2_runtime_smoke_runbook_preview,
)
from decodilo.lambda_cloud.remote_vslice_expected_artifact_policy import (
    load_lambda_remote_vslice_expected_artifact_policy,
)
from decodilo.lambda_cloud.remote_vslice_failure_artifact_capture_policy import (
    load_lambda_remote_vslice_failure_artifact_capture_policy,
)
from decodilo.lambda_cloud.runtime_smoke_failure_closeout import (
    load_lambda_runtime_smoke_failure_closeout,
)
from decodilo.lambda_cloud.runtime_smoke_failure_evidence_policy import (
    load_lambda_runtime_smoke_failure_evidence_policy,
)
from decodilo.lambda_cloud.runtime_smoke_failure_record import (
    load_lambda_runtime_smoke_failure_record,
)


class LambdaM075SReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M075S"
    report_passed: bool
    failure_status: str
    closeout_status: str
    failure_evidence_policy_status: str
    artifact_policy_status: str
    capture_policy_passed: bool
    m075r2_authorization_status: str
    runbook_preview_status: str
    infrastructure_passed: bool
    failure_evidence_insufficient: bool
    historical_billable_action_performed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_report(self) -> LambdaM075SReport:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("M075S report must not authorize launch or spend")
        if self.report_passed and self.blockers:
            raise ValueError("passing M075S report cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m075s_report_from_paths(
    *,
    failure_record: str | Path,
    failure_closeout: str | Path,
    failure_evidence_policy: str | Path,
    artifact_policy: str | Path,
    capture_policy: str | Path,
    authorization: str | Path,
    runbook_preview: str | Path,
) -> LambdaM075SReport:
    record = load_lambda_runtime_smoke_failure_record(failure_record)
    closeout = load_lambda_runtime_smoke_failure_closeout(failure_closeout)
    evidence_policy = load_lambda_runtime_smoke_failure_evidence_policy(
        failure_evidence_policy
    )
    artifact = load_lambda_remote_vslice_expected_artifact_policy(artifact_policy)
    capture = load_lambda_remote_vslice_failure_artifact_capture_policy(capture_policy)
    auth = load_lambda_m075r2_runtime_smoke_retry_authorization(authorization)
    preview = load_lambda_m075r2_runtime_smoke_runbook_preview(runbook_preview)
    blockers: list[str] = []
    if record.failure_status != "runtime_smoke_command_failed":
        blockers.append("runtime_smoke_failure_not_classified")
    if not closeout.closeout_succeeded:
        blockers.append("failure_closeout_not_succeeded")
    if evidence_policy.policy_status != "policy_defined":
        blockers.append("failure_evidence_policy_not_defined")
    if artifact.policy_status != "policy_defined":
        blockers.append("expected_artifact_policy_not_defined")
    if not capture.policy_passed:
        blockers.append("capture_policy_not_passed")
    if auth.authorization_status != "authorized_for_future_m075r2_runtime_smoke_retry":
        blockers.append("m075r2_not_authorized")
    if preview.preview_status != "ready_for_future_m075r2_runtime_smoke_retry_review":
        blockers.append("m075r2_runbook_preview_not_ready")
    return LambdaM075SReport(
        report_passed=not blockers,
        failure_status=record.failure_status,
        closeout_status=closeout.closeout_status,
        failure_evidence_policy_status=evidence_policy.policy_status,
        artifact_policy_status=artifact.policy_status,
        capture_policy_passed=capture.policy_passed,
        m075r2_authorization_status=auth.authorization_status,
        runbook_preview_status=preview.preview_status,
        infrastructure_passed=record.infrastructure_passed,
        failure_evidence_insufficient=closeout.failure_evidence_insufficient,
        historical_billable_action_performed=record.historical_billable_action_performed,
        blockers=sorted(set(blockers)),
        warnings=[
            "M075S is offline; M075R2 still requires fresh discovery and supervised approval",
        ],
    )


def load_lambda_m075s_report(path: str | Path) -> LambdaM075SReport:
    return LambdaM075SReport.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_m075s_report(path: str | Path, report: LambdaM075SReport) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
