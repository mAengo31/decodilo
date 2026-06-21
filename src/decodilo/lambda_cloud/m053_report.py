"""M053 report for future SSH-connectivity-only planning."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.m054_ssh_connectivity_authorization import (
    load_lambda_m054_ssh_connectivity_authorization,
)
from decodilo.lambda_cloud.m054_ssh_connectivity_runbook_preview import (
    load_lambda_m054_ssh_connectivity_runbook_preview,
)
from decodilo.lambda_cloud.ssh_connectivity_risk_review import (
    load_lambda_ssh_connectivity_risk_review,
)
from decodilo.lambda_cloud.ssh_connectivity_scope import load_lambda_ssh_connectivity_scope


class LambdaM053Report(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    scope_status: str
    credential_policy_status: str | None = None
    client_policy_status: str | None = None
    operator_approval_status: str
    remote_command_prohibition_status: str | None = None
    file_transfer_prohibition_status: str | None = None
    port_forwarding_prohibition_status: str | None = None
    risk_review_status: str
    m054_authorization_status: str
    runbook_preview_status: str
    report_passed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_planning_only(self) -> LambdaM053Report:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M053 report cannot enable launch or SSH")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m053_report_from_paths(
    *,
    scope: str | Path,
    risk_review: str | Path,
    authorization: str | Path,
    runbook_preview: str | Path,
) -> LambdaM053Report:
    scope_report = load_lambda_ssh_connectivity_scope(scope)
    risk = load_lambda_ssh_connectivity_risk_review(risk_review)
    auth = load_lambda_m054_ssh_connectivity_authorization(authorization)
    preview = load_lambda_m054_ssh_connectivity_runbook_preview(runbook_preview)
    blocking_errors = [
        blocker
        for blocker in [*scope_report.blockers, *risk.blockers]
        if blocker != "operator_approval_not_provided"
    ]
    report_passed = not blocking_errors
    return LambdaM053Report(
        scope_status=scope_report.scope_status,
        credential_policy_status=(
            "policy_defined"
            if "ssh_credential_policy_not_defined" not in risk.blockers
            else "blocked"
        ),
        client_policy_status="policy_defined",
        operator_approval_status=risk.operator_approval_status,
        remote_command_prohibition_status="remote_commands_prohibited",
        file_transfer_prohibition_status="file_transfer_prohibited",
        port_forwarding_prohibition_status="port_forwarding_prohibited",
        risk_review_status=risk.risk_review_status,
        m054_authorization_status=auth.authorization_status,
        runbook_preview_status=preview.preview_status,
        report_passed=report_passed,
        blockers=sorted(set(blocking_errors)),
        warnings=sorted(
            set(
                [
                    "M053 is planning/review only and performs no Lambda or SSH operation",
                    *scope_report.warnings,
                    *risk.warnings,
                    *auth.warnings,
                    *preview.warnings,
                ]
            )
        ),
    )


def load_lambda_m053_report(path: str | Path) -> LambdaM053Report:
    return LambdaM053Report.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_m053_report(path: str | Path, report: LambdaM053Report) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
