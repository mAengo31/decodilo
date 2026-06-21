"""M050 report for remote runtime bootstrap planning."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.bootstrap_risk_review import (
    load_lambda_bootstrap_risk_review,
)
from decodilo.lambda_cloud.m051_bootstrap_authorization import (
    load_lambda_m051_bootstrap_authorization,
)
from decodilo.lambda_cloud.m051_bootstrap_runbook_preview import (
    load_lambda_m051_bootstrap_runbook_preview,
)
from decodilo.lambda_cloud.remote_access_policy import load_lambda_remote_access_policy
from decodilo.lambda_cloud.remote_bootstrap_scope import load_lambda_remote_bootstrap_scope


class LambdaM050Report(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    report_passed: bool
    selected_bootstrap_mode: str | None = None
    bootstrap_scope_status: str
    access_policy_status: str
    ssh_approval_status: str
    command_allowlist_status: str
    package_install_policy_status: str
    no_training_policy_status: str
    evidence_schema_status: str
    risk_review_passed: bool
    m051_authorization_status: str
    runbook_preview_status: str
    future_m051_review_authorized: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_m050_disabled(self) -> LambdaM050Report:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M050 report cannot enable launch or mutation")
        if self.report_passed and self.blockers:
            raise ValueError("M050 report cannot pass with blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m050_report_from_paths(
    *,
    scope: str | Path,
    access_policy: str | Path,
    risk_review: str | Path,
    authorization: str | Path,
    runbook_preview: str | Path,
) -> LambdaM050Report:
    scope_report = load_lambda_remote_bootstrap_scope(scope)
    access = load_lambda_remote_access_policy(access_policy)
    risk = load_lambda_bootstrap_risk_review(risk_review)
    auth = load_lambda_m051_bootstrap_authorization(authorization)
    preview = load_lambda_m051_bootstrap_runbook_preview(runbook_preview)
    blockers = [
        *scope_report.blockers,
        *access.blockers,
        *risk.blockers,
        *auth.blockers,
        *preview.blockers,
    ]
    if not risk.risk_review_passed:
        blockers.append("bootstrap_risk_review_not_passed")
    if auth.authorization_status == "not_authorized":
        blockers.append("m051_bootstrap_authorization_not_ready")
    if preview.preview_status != "ready_for_future_m051_bootstrap_review":
        blockers.append("m051_bootstrap_runbook_preview_not_ready")
    return LambdaM050Report(
        report_passed=not blockers,
        selected_bootstrap_mode=auth.selected_bootstrap_mode,
        bootstrap_scope_status=scope_report.bootstrap_scope_status,
        access_policy_status=access.access_policy_status,
        ssh_approval_status=risk.ssh_approval_status,
        command_allowlist_status=risk.command_allowlist_status,
        package_install_policy_status=risk.package_install_policy_status,
        no_training_policy_status=risk.no_training_policy_status,
        evidence_schema_status=risk.evidence_schema_status,
        risk_review_passed=risk.risk_review_passed,
        m051_authorization_status=auth.authorization_status,
        runbook_preview_status=preview.preview_status,
        future_m051_review_authorized=auth.future_review_authorized,
        blockers=sorted(set(blockers)),
        warnings=sorted(
            set(
                [
                    "M050 is planning-only and performs no Lambda API calls",
                    "M051 authorization is future-only and non-executable",
                    *scope_report.warnings,
                    *access.warnings,
                    *risk.warnings,
                    *auth.warnings,
                    *preview.warnings,
                ]
            )
        ),
    )


def load_lambda_m050_report(path: str | Path) -> LambdaM050Report:
    return LambdaM050Report.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_m050_report(path: str | Path, report: LambdaM050Report) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
