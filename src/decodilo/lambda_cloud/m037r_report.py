"""M037R lower-cost Strand-compatible reauthorization report."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.lower_cost_future_launch_decision import (
    LambdaLowerCostFutureLaunchDecision,
    load_lambda_lower_cost_future_launch_decision,
)


class LambdaM037RReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    lower_cost_shape: str = "gpu_1x_h100_pcie"
    strand_payload_compatible: bool
    existing_ssh_key_required: bool = True
    lower_cost_authorization_status: str
    future_launch_decision: str
    future_launch_review_authorized: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaM037RReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M037R report cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m037r_report(
    *,
    decision: LambdaLowerCostFutureLaunchDecision,
) -> LambdaM037RReport:
    status = (
        "authorized_for_future_lower_cost_launch_review"
        if decision.future_launch_review_authorized
        else "not_authorized"
    )
    return LambdaM037RReport(
        strand_payload_compatible=decision.future_launch_review_authorized,
        lower_cost_authorization_status=status,
        future_launch_decision=decision.decision_status,
        future_launch_review_authorized=decision.future_launch_review_authorized,
        blockers=decision.blockers,
        warnings=[
            *decision.warnings,
            "M037R is no-launch/no-termination/no-mutation",
        ],
    )


def build_lambda_m037r_report_from_path(
    *,
    decision: str | Path,
) -> LambdaM037RReport:
    return build_lambda_m037r_report(
        decision=load_lambda_lower_cost_future_launch_decision(decision)
    )


def load_lambda_m037r_report(path: str | Path) -> LambdaM037RReport:
    return LambdaM037RReport.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_m037r_report(path: str | Path, report: LambdaM037RReport) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
