"""M045 report for capacity-history-selected future launch review."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.capacity_selected_command_preview import (
    load_lambda_capacity_selected_command_preview,
)
from decodilo.lambda_cloud.capacity_selected_cost_risk_review import (
    load_lambda_capacity_selected_cost_risk_review,
)
from decodilo.lambda_cloud.capacity_selected_gate_check import (
    load_lambda_capacity_selected_gate_check,
)
from decodilo.lambda_cloud.capacity_selected_m046_authorization import (
    load_lambda_capacity_selected_m046_authorization,
)
from decodilo.lambda_cloud.capacity_selected_operator_approval import (
    load_lambda_capacity_selected_operator_approval,
)
from decodilo.lambda_cloud.m045_decision_record import load_lambda_m045_decision_record


class LambdaM045Report(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    selected_candidate: str | None = None
    cost_risk_review_status: str
    operator_approval_status: str
    m046_authorization_status: str | None = None
    gate_check_status: str | None = None
    command_preview_status: str | None = None
    decision_status: str
    future_launch_candidate: bool = False
    report_passed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaM045Report:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M045 report cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m045_report_from_paths(
    *,
    cost_risk_review: str | Path,
    operator_approval: str | Path,
    decision: str | Path,
    authorization: str | Path | None = None,
    gate_check: str | Path | None = None,
    command_preview: str | Path | None = None,
) -> LambdaM045Report:
    cost = load_lambda_capacity_selected_cost_risk_review(cost_risk_review)
    approval = load_lambda_capacity_selected_operator_approval(operator_approval)
    decision_record = load_lambda_m045_decision_record(decision)
    auth = (
        None
        if authorization is None or not Path(authorization).exists()
        else load_lambda_capacity_selected_m046_authorization(authorization)
    )
    gate = (
        None
        if gate_check is None or not Path(gate_check).exists()
        else load_lambda_capacity_selected_gate_check(gate_check)
    )
    preview = (
        None
        if command_preview is None or not Path(command_preview).exists()
        else load_lambda_capacity_selected_command_preview(command_preview)
    )
    blockers = [
        *cost.blockers,
        *approval.blockers,
        *decision_record.blockers,
        *(auth.blockers if auth is not None else []),
        *(gate.blockers if gate is not None else []),
        *(preview.blockers if preview is not None else []),
    ]
    accepted_path = (
        decision_record.decision_status
        == "authorize_future_m046_capacity_selected_launch_review"
    )
    report_passed = (
        accepted_path
        and auth is not None
        and gate is not None
        and preview is not None
        and auth.authorization_status
        == "authorized_for_future_m046_capacity_selected_launch_review"
        and gate.gate_passed
        and preview.preview_status == "ready_for_future_m046_capacity_selected_review"
        and not blockers
    )
    declined_path = decision_record.decision_status in {
        "wait_for_live_availability",
        "require_manual_candidate_selection",
    }
    return LambdaM045Report(
        selected_candidate=(
            auth.selected_candidate
            if auth is not None and auth.selected_candidate is not None
            else cost.selected_candidate
        ),
        cost_risk_review_status=(
            "passed" if cost.cost_risk_review_passed else "blocked"
        ),
        operator_approval_status=approval.approval_status,
        m046_authorization_status=None if auth is None else auth.authorization_status,
        gate_check_status=None if gate is None else ("passed" if gate.gate_passed else "blocked"),
        command_preview_status=None if preview is None else preview.preview_status,
        decision_status=decision_record.decision_status,
        future_launch_candidate=report_passed,
        report_passed=report_passed or (declined_path and not blockers),
        blockers=sorted(set(blockers)),
        warnings=sorted(
            set(
                [
                    "M045 is review-only and cannot launch",
                    "future launch requires a separate supervised milestone",
                    *cost.warnings,
                    *approval.warnings,
                    *decision_record.warnings,
                    *(auth.warnings if auth is not None else []),
                    *(gate.warnings if gate is not None else []),
                    *(preview.warnings if preview is not None else []),
                ]
            )
        ),
    )


def load_lambda_m045_report(path: str | Path) -> LambdaM045Report:
    return LambdaM045Report.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_m045_report(path: str | Path, report: LambdaM045Report) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
