"""M058 closeout report for the completed M057 SSH no-op command run."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.m059_command_runbook_preview import (
    load_lambda_m059_command_runbook_preview,
)
from decodilo.lambda_cloud.m059_remote_command_authorization import (
    load_lambda_m059_remote_command_authorization,
)
from decodilo.lambda_cloud.remote_command_stage_policy import (
    load_lambda_remote_command_stage_policy,
)
from decodilo.lambda_cloud.smallest_useful_command_review import (
    load_lambda_smallest_useful_command_review,
)
from decodilo.lambda_cloud.ssh_noop_command_closeout import (
    load_lambda_ssh_noop_command_closeout,
)
from decodilo.lambda_cloud.ssh_noop_command_reconciliation import (
    load_lambda_ssh_noop_command_reconciliation,
)
from decodilo.lambda_cloud.ssh_noop_command_success_record import (
    load_lambda_ssh_noop_command_success_record,
)


class LambdaM058Report(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    success_record_status: str
    reconciliation_status: str
    closeout_status: str
    stage_policy_status: str
    selected_future_command_set: list[str] = Field(default_factory=list)
    m059_authorization_status: str
    runbook_preview_status: str
    selected_candidate: str | None = None
    selected_region: str | None = None
    report_passed: bool
    historical_billable_action_performed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_closeout_only(self) -> LambdaM058Report:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M058 report cannot enable launch or mutation")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m058_report_from_paths(
    *,
    success_record: str | Path,
    reconciliation: str | Path,
    closeout: str | Path,
    stage_policy: str | Path,
    command_review: str | Path,
    authorization: str | Path,
    runbook_preview: str | Path,
) -> LambdaM058Report:
    success = load_lambda_ssh_noop_command_success_record(success_record)
    reconcile = load_lambda_ssh_noop_command_reconciliation(reconciliation)
    close = load_lambda_ssh_noop_command_closeout(closeout)
    policy = load_lambda_remote_command_stage_policy(stage_policy)
    review = load_lambda_smallest_useful_command_review(command_review)
    auth = load_lambda_m059_remote_command_authorization(authorization)
    preview = load_lambda_m059_command_runbook_preview(runbook_preview)
    blockers = [
        *success.blockers,
        *reconcile.errors,
        *close.blockers,
        *policy.blockers,
        *review.blockers,
        *auth.blockers,
        *preview.blockers,
    ]
    if success.status != "ssh_noop_command_success":
        blockers.append("ssh_noop_success_record_not_success")
    if not reconcile.reconciliation_passed:
        blockers.append("ssh_noop_reconciliation_not_passed")
    if not close.closeout_succeeded:
        blockers.append("ssh_noop_closeout_not_succeeded")
    if policy.current_accepted_stage != "noop_command_only":
        blockers.append("remote_command_stage_policy_not_noop")
    if (
        auth.authorization_status
        != "authorized_for_future_m059_identity_command_review"
    ):
        blockers.append("m059_authorization_not_ready")
    if preview.preview_status != "ready_for_future_m059_identity_command_review":
        blockers.append("m059_runbook_preview_not_ready")
    return LambdaM058Report(
        success_record_status=success.status,
        reconciliation_status="passed" if reconcile.reconciliation_passed else "blocked",
        closeout_status=close.closeout_status,
        stage_policy_status=policy.current_accepted_stage,
        selected_future_command_set=auth.selected_future_command_set,
        m059_authorization_status=auth.authorization_status,
        runbook_preview_status=preview.preview_status,
        selected_candidate=success.selected_candidate,
        selected_region=success.selected_region,
        report_passed=not blockers,
        historical_billable_action_performed=success.historical_billable_action_performed,
        blockers=sorted(set(blockers)),
        warnings=sorted(
            set(
                [
                    "M058 is closeout-only and performs no Lambda operation",
                    *success.warnings,
                    *reconcile.warnings,
                    *close.warnings,
                    *policy.warnings,
                    *review.warnings,
                    *auth.warnings,
                    *preview.warnings,
                ]
            )
        ),
    )


def load_lambda_m058_report(path: str | Path) -> LambdaM058Report:
    return LambdaM058Report.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_m058_report(path: str | Path, report: LambdaM058Report) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
