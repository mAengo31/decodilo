"""M060 offline closeout report for the M059 hostname identity command run."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.m061_next_step_decision import (
    load_lambda_m061_next_step_decision,
)
from decodilo.lambda_cloud.ssh_hostname_identity_closeout import (
    load_lambda_ssh_hostname_identity_closeout,
)
from decodilo.lambda_cloud.ssh_hostname_identity_evidence_package import (
    load_lambda_ssh_hostname_identity_evidence_package,
)
from decodilo.lambda_cloud.ssh_hostname_identity_reconciliation import (
    load_lambda_ssh_hostname_identity_reconciliation,
)
from decodilo.lambda_cloud.ssh_hostname_identity_success_record import (
    load_lambda_ssh_hostname_identity_success_record,
)


class LambdaM060Report(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    success_record_status: str
    reconciliation_status: str
    evidence_complete: bool
    closeout_status: str
    m061_decision: str
    m061_authorization_status: str | None = None
    next_allowed_review_command: str | None = None
    selected_candidate: str | None = None
    selected_region: str | None = None
    command: str = "hostname"
    stdout_captured_redacted: bool
    termination_verified: bool
    final_instance_count: int
    final_unmanaged_count: int
    report_passed: bool
    historical_billable_action_performed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_closeout_only(self) -> LambdaM060Report:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M060 report cannot enable launch or mutation")
        if self.command != "hostname":
            raise ValueError("M060 report can only close hostname")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m060_report_from_paths(
    *,
    success_record: str | Path,
    reconciliation: str | Path,
    evidence_package: str | Path,
    closeout: str | Path,
    decision: str | Path,
    authorization: str | Path | None = None,
) -> LambdaM060Report:
    success = load_lambda_ssh_hostname_identity_success_record(success_record)
    reconcile = load_lambda_ssh_hostname_identity_reconciliation(reconciliation)
    evidence = load_lambda_ssh_hostname_identity_evidence_package(evidence_package)
    close = load_lambda_ssh_hostname_identity_closeout(closeout)
    next_decision = load_lambda_m061_next_step_decision(decision)
    if authorization:
        from decodilo.lambda_cloud.m061_whoami_authorization import (
            load_lambda_m061_whoami_authorization,
        )

        auth = load_lambda_m061_whoami_authorization(authorization)
    else:
        auth = None
    blockers = [
        *success.blockers,
        *reconcile.errors,
        *evidence.blockers,
        *close.blockers,
        *next_decision.blockers,
        *(auth.blockers if auth is not None else []),
    ]
    if success.status != "ssh_hostname_identity_success":
        blockers.append("hostname_success_record_not_success")
    if not reconcile.reconciliation_passed:
        blockers.append("hostname_reconciliation_not_passed")
    if not evidence.evidence_complete:
        blockers.append("hostname_evidence_package_incomplete")
    if not close.closeout_succeeded:
        blockers.append("hostname_closeout_not_succeeded")
    if next_decision.decision_status != "plan_whoami_identity_command_review":
        blockers.append("m061_decision_not_ready_for_whoami_review")
    if auth is not None and (
        auth.authorization_status
        != "authorized_for_future_m061_whoami_identity_command_review"
    ):
        blockers.append("m061_authorization_not_ready")
    return LambdaM060Report(
        success_record_status=success.status,
        reconciliation_status="passed" if reconcile.reconciliation_passed else "blocked",
        evidence_complete=evidence.evidence_complete,
        closeout_status=close.closeout_status,
        m061_decision=next_decision.decision_status,
        m061_authorization_status=(
            auth.authorization_status if auth is not None else None
        ),
        next_allowed_review_command=next_decision.next_allowed_review_command,
        selected_candidate=success.selected_candidate,
        selected_region=success.selected_region,
        stdout_captured_redacted=success.stdout_captured_redacted,
        termination_verified=success.termination_verified,
        final_instance_count=success.final_instance_count,
        final_unmanaged_count=success.final_unmanaged_count,
        report_passed=not blockers,
        historical_billable_action_performed=success.historical_billable_action_performed,
        blockers=sorted(set(blockers)),
        warnings=sorted(
            set(
                [
                    "M060 is closeout-only and performs no Lambda operation",
                    *success.warnings,
                    *reconcile.warnings,
                    *evidence.warnings,
                    *close.warnings,
                    *next_decision.warnings,
                    *(auth.warnings if auth is not None else []),
                ]
            )
        ),
    )


def load_lambda_m060_report(path: str | Path) -> LambdaM060Report:
    return LambdaM060Report.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_m060_report(path: str | Path, report: LambdaM060Report) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
