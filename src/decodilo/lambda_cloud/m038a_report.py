"""M038A final future-only lower-cost M039 launch review report."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.lower_cost_gate_check import (
    LambdaLowerCostGateCheck,
    load_lambda_lower_cost_gate_check,
)
from decodilo.lambda_cloud.lower_cost_launch_command_preview import (
    LambdaLowerCostLaunchCommandPreview,
    load_lambda_lower_cost_launch_command_preview,
)
from decodilo.lambda_cloud.lower_cost_m039_authorization import (
    LambdaLowerCostM039Authorization,
    load_lambda_lower_cost_m039_authorization,
)
from decodilo.lambda_cloud.lower_cost_operator_approval import (
    LambdaLowerCostOperatorApproval,
    load_lambda_lower_cost_operator_approval,
)


class LambdaM038AReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    operator_approval_status: str
    m039_authorization_status: str
    gate_check_status: str
    command_preview_status: str
    selected_shape: str
    estimated_30min_cost: float | None = None
    buffered_estimated_30min_cost: float | None = None
    selected_ssh_key_hash: str | None = None
    future_launch_candidate: bool
    report_passed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaM038AReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M038A report cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m038a_report(
    *,
    authorization: LambdaLowerCostM039Authorization,
    gate_check: LambdaLowerCostGateCheck,
    command_preview: LambdaLowerCostLaunchCommandPreview,
    operator_approval: LambdaLowerCostOperatorApproval,
) -> LambdaM038AReport:
    blockers = sorted(
        set(
            [
                *operator_approval.blockers,
                *authorization.blockers,
                *gate_check.blockers,
                *command_preview.blockers,
            ]
        )
    )
    future_launch_candidate = (
        operator_approval.approval_status
        == "approved_for_future_m039_lower_cost_launch_attempt"
        and authorization.authorization_status
        == "authorized_for_future_m039_lower_cost_launch_attempt"
        and gate_check.gate_passed
        and command_preview.preview_status == "ready_for_future_m039"
        and not blockers
    )
    return LambdaM038AReport(
        operator_approval_status=operator_approval.approval_status,
        m039_authorization_status=authorization.authorization_status,
        gate_check_status="passed" if gate_check.gate_passed else "blocked",
        command_preview_status=command_preview.preview_status,
        selected_shape=authorization.selected_shape,
        estimated_30min_cost=authorization.estimated_30min_cost,
        buffered_estimated_30min_cost=authorization.buffered_estimated_30min_cost,
        selected_ssh_key_hash=authorization.selected_ssh_key_hash,
        future_launch_candidate=future_launch_candidate,
        report_passed=future_launch_candidate,
        blockers=blockers,
        warnings=[
            "M038A approves only future M039 review; it does not launch",
            "M039 remains separately operator-supervised and billable",
            *operator_approval.warnings,
            *authorization.warnings,
            *gate_check.warnings,
            *command_preview.warnings,
        ],
    )


def build_lambda_m038a_report_from_paths(
    *,
    authorization: str | Path,
    gate_check: str | Path,
    command_preview: str | Path,
    operator_approval: str | Path,
) -> LambdaM038AReport:
    return build_lambda_m038a_report(
        authorization=load_lambda_lower_cost_m039_authorization(authorization),
        gate_check=load_lambda_lower_cost_gate_check(gate_check),
        command_preview=load_lambda_lower_cost_launch_command_preview(command_preview),
        operator_approval=load_lambda_lower_cost_operator_approval(operator_approval),
    )


def load_lambda_m038a_report(path: str | Path) -> LambdaM038AReport:
    return LambdaM038AReport.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_m038a_report(path: str | Path, report: LambdaM038AReport) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
