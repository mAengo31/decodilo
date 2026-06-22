"""M055D capacity closeout and future M056 SSH retry report."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.ssh_capacity_history import load_lambda_ssh_capacity_history
from decodilo.lambda_cloud.ssh_capacity_retry_closeout import (
    load_lambda_ssh_capacity_retry_closeout,
)
from decodilo.lambda_cloud.ssh_live_candidate_selector import (
    load_lambda_ssh_live_candidate_selection,
)
from decodilo.lambda_cloud.ssh_retry_candidate_policy import (
    load_lambda_ssh_retry_candidate_policy,
)
from decodilo.lambda_cloud.ssh_retry_command_preview import (
    load_lambda_ssh_retry_command_preview,
)
from decodilo.lambda_cloud.ssh_retry_future_authorization import (
    load_lambda_ssh_retry_future_authorization,
)
from decodilo.lambda_cloud.ssh_retry_operator_decision import (
    load_lambda_ssh_retry_operator_decision,
)


class LambdaM055DReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M055D"
    report_passed: bool
    capacity_closeout_status: str
    capacity_rejections_count: int
    ssh_layer_failures_count: int
    live_candidate_selection_status: str
    selected_candidate: str | None = None
    selected_region: str | None = None
    retry_policy_status: str
    operator_decision_status: str
    m056_authorization_status: str
    command_preview_status: str
    same_candidate_region_retry_blocked: bool
    billable_action_performed: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    real_mutation_enabled: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_disabled(self) -> LambdaM055DReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M055D report cannot enable launch")
        if self.report_passed and self.blockers:
            raise ValueError("passing M055D report cannot include blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m055d_report_from_paths(
    *,
    capacity_closeout: str | Path,
    capacity_history: str | Path,
    candidate_selection: str | Path,
    retry_policy: str | Path,
    operator_decision: str | Path,
    authorization: str | Path,
    command_preview: str | Path,
) -> LambdaM055DReport:
    closeout = load_lambda_ssh_capacity_retry_closeout(capacity_closeout)
    history = load_lambda_ssh_capacity_history(capacity_history)
    selection = load_lambda_ssh_live_candidate_selection(candidate_selection)
    policy = load_lambda_ssh_retry_candidate_policy(retry_policy)
    decision = load_lambda_ssh_retry_operator_decision(operator_decision)
    auth = load_lambda_ssh_retry_future_authorization(authorization)
    preview = load_lambda_ssh_retry_command_preview(command_preview)
    blockers = [
        *closeout.blockers,
        *history.blockers,
        *selection.blockers,
        *policy.blockers,
        *decision.blockers,
        *auth.blockers,
        *preview.blockers,
    ]
    report_passed = (
        closeout.closeout_succeeded
        and selection.selection_status == "selected_live_candidate"
        and policy.policy_status == "policy_passed"
        and decision.decision_status == "authorize_future_live_candidate_ssh_retry_review"
        and auth.authorization_status
        == "authorized_for_future_m056_live_candidate_ssh_retry_review"
        and preview.preview_status == "ready_for_future_m056_live_candidate_ssh_retry_review"
        and not blockers
    )
    return LambdaM055DReport(
        report_passed=report_passed,
        capacity_closeout_status=closeout.closeout_status,
        capacity_rejections_count=history.capacity_rejections_count,
        ssh_layer_failures_count=history.ssh_layer_failures_count,
        live_candidate_selection_status=selection.selection_status,
        selected_candidate=selection.selected_candidate,
        selected_region=selection.selected_region,
        retry_policy_status=policy.policy_status,
        operator_decision_status=decision.decision_status,
        m056_authorization_status=auth.authorization_status,
        command_preview_status=preview.preview_status,
        same_candidate_region_retry_blocked=closeout.same_candidate_region_retry_blocked,
        blockers=sorted(set(blockers)),
        warnings=[
            *closeout.warnings,
            *history.warnings,
            *selection.warnings,
            *policy.warnings,
            *decision.warnings,
            *auth.warnings,
            *preview.warnings,
        ],
    )


def load_lambda_m055d_report(path: str | Path) -> LambdaM055DReport:
    return LambdaM055DReport.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_m055d_report(path: str | Path, report: LambdaM055DReport) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
