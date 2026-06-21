"""M053A explicit SSH-connectivity operator decision report."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.m054_ssh_connectivity_authorization import (
    load_lambda_m054_ssh_connectivity_authorization,
)
from decodilo.lambda_cloud.m054_ssh_connectivity_runbook_preview import (
    load_lambda_m054_ssh_connectivity_runbook_preview,
)
from decodilo.lambda_cloud.ssh_connectivity_operator_approval import (
    load_lambda_ssh_connectivity_operator_approval,
)
from decodilo.lambda_cloud.ssh_connectivity_risk_review import (
    load_lambda_ssh_connectivity_risk_review,
)

LambdaM053AOperatorChoice = Literal[
    "approve_future_m054_ssh_connectivity_only_review",
    "pause_remote_access_keep_m054_not_authorized",
    "not_provided",
]


class LambdaM053AReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    operator_choice: LambdaM053AOperatorChoice
    operator_approval_status: str
    risk_review_status: str
    m054_authorization_status: str
    runbook_preview_status: str
    report_passed: bool
    ssh_now: bool = False
    run_command_now: bool = False
    launch_now: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_no_execution(self) -> LambdaM053AReport:
        if (
            self.ssh_now
            or self.run_command_now
            or self.launch_now
            or self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M053A cannot authorize immediate launch, SSH, or commands")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def _choice_from_approval_status(status: str) -> LambdaM053AOperatorChoice:
    if status == "approved_for_future_m054_ssh_connectivity_review":
        return "approve_future_m054_ssh_connectivity_only_review"
    if status == "declined":
        return "pause_remote_access_keep_m054_not_authorized"
    return "not_provided"


def build_lambda_m053a_report_from_paths(
    *,
    operator_approval: str | Path,
    risk_review: str | Path,
    authorization: str | Path,
    runbook_preview: str | Path,
) -> LambdaM053AReport:
    approval = load_lambda_ssh_connectivity_operator_approval(operator_approval)
    risk = load_lambda_ssh_connectivity_risk_review(risk_review)
    auth = load_lambda_m054_ssh_connectivity_authorization(authorization)
    preview = load_lambda_m054_ssh_connectivity_runbook_preview(runbook_preview)

    choice = _choice_from_approval_status(approval.approval_status)
    blockers = [
        *approval.blockers,
        *risk.blockers,
        *auth.blockers,
        *preview.blockers,
    ]

    if choice == "not_provided":
        blockers.append("operator_choice_not_provided")
    elif choice == "approve_future_m054_ssh_connectivity_only_review":
        if not approval.approval_complete:
            blockers.append("operator_approval_incomplete")
        if risk.risk_review_status != "passed" or not risk.risk_review_passed:
            blockers.append("ssh_connectivity_risk_review_not_passed")
        if (
            auth.authorization_status
            != "authorized_for_future_m054_ssh_connectivity_review"
        ):
            blockers.append("m054_future_authorization_missing")
        if preview.preview_status != "ready_for_future_m054_ssh_connectivity_review":
            blockers.append("m054_runbook_preview_not_ready")
    elif choice == "pause_remote_access_keep_m054_not_authorized":
        blockers = [
            blocker for blocker in blockers if blocker != "operator_approval_declined"
        ]
        if auth.authorization_status != "not_authorized":
            blockers.append("declined_path_authorized_unexpectedly")
        if preview.preview_status != "blocked_not_authorized":
            blockers.append("declined_path_runbook_not_blocked")

    return LambdaM053AReport(
        operator_choice=choice,
        operator_approval_status=approval.approval_status,
        risk_review_status=risk.risk_review_status,
        m054_authorization_status=auth.authorization_status,
        runbook_preview_status=preview.preview_status,
        report_passed=not blockers,
        blockers=sorted(set(blockers)),
        warnings=sorted(
            set(
                [
                    "M053A applies an explicit operator decision only; it does not execute SSH",
                    "M054 remains a separate supervised milestone",
                    *approval.warnings,
                    *risk.warnings,
                    *auth.warnings,
                    *preview.warnings,
                ]
            )
        ),
    )


def load_lambda_m053a_report(path: str | Path) -> LambdaM053AReport:
    return LambdaM053AReport.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_m053a_report(path: str | Path, report: LambdaM053AReport) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
