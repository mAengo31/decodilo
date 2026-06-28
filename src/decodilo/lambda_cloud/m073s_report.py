"""Aggregate M073S upload-readiness closeout and retry-planning report."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.m073r2_retry_authorization import (
    load_lambda_m073r2_retry_authorization,
)
from decodilo.lambda_cloud.m073r2_runbook_preview import (
    load_lambda_m073r2_runbook_preview,
)
from decodilo.lambda_cloud.remote_vslice_upload_closeout import (
    load_lambda_remote_vslice_upload_closeout,
)
from decodilo.lambda_cloud.source_bundle_upload_policy import (
    load_lambda_source_dependency_upload_policy,
)
from decodilo.lambda_cloud.ssh_banner_readiness_policy import (
    load_lambda_ssh_banner_readiness_policy,
)
from decodilo.lambda_cloud.upload_failure_classifier import (
    load_lambda_upload_failure_classification,
)


class LambdaM073SReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M073S"
    report_passed: bool
    classification: str
    closeout_status: str
    banner_readiness_policy_status: str
    upload_policy_status: str
    m073r2_authorization_status: str
    runbook_preview_status: str
    decodilo_not_tested: bool
    historical_billable_action_performed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_report(self) -> LambdaM073SReport:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("M073S report must not authorize launch or spend")
        if self.report_passed and self.blockers:
            raise ValueError("passing M073S report cannot carry blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m073s_report_from_paths(
    *,
    classification: str | Path,
    closeout: str | Path,
    banner_policy: str | Path,
    upload_policy: str | Path,
    authorization: str | Path,
    runbook_preview: str | Path,
) -> LambdaM073SReport:
    cls = load_lambda_upload_failure_classification(classification)
    close = load_lambda_remote_vslice_upload_closeout(closeout)
    banner = load_lambda_ssh_banner_readiness_policy(banner_policy)
    upload = load_lambda_source_dependency_upload_policy(upload_policy)
    auth = load_lambda_m073r2_retry_authorization(authorization)
    preview = load_lambda_m073r2_runbook_preview(runbook_preview)
    blockers: list[str] = []
    if cls.failure_classification not in {
        "ssh_banner_exchange_timeout_during_upload",
        "scp_connection_closed_during_upload",
    }:
        blockers.append("classification_not_upload_readiness_failure")
    if not close.closeout_succeeded:
        blockers.append("upload_closeout_not_succeeded")
    if not banner.banner_readiness_required_before_upload:
        blockers.append("banner_readiness_not_required")
    if upload.upload_policy_status != "policy_defined":
        blockers.append("upload_policy_not_defined")
    if auth.authorization_status != "authorized_for_future_m073r2_tiny_smoke_retry":
        blockers.append("m073r2_not_authorized")
    if preview.preview_status != "ready_for_future_m073r2_tiny_smoke_retry_review":
        blockers.append("m073r2_runbook_preview_not_ready")
    return LambdaM073SReport(
        report_passed=not blockers,
        classification=cls.failure_classification,
        closeout_status=close.closeout_status,
        banner_readiness_policy_status=banner.policy_status,
        upload_policy_status=upload.upload_policy_status,
        m073r2_authorization_status=auth.authorization_status,
        runbook_preview_status=preview.preview_status,
        decodilo_not_tested=close.decodilo_not_tested,
        historical_billable_action_performed=close.historical_billable_action_performed,
        blockers=blockers,
        warnings=[
            "M073S is offline; M073R2 still requires fresh discovery and operator approval",
        ],
    )


def load_lambda_m073s_report(path: str | Path) -> LambdaM073SReport:
    return LambdaM073SReport.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_m073s_report(path: str | Path, report: LambdaM073SReport) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
