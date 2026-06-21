"""M044 catalog-rotation decision report."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.catalog_rotation_command_preview import (
    load_lambda_catalog_rotation_command_preview,
)
from decodilo.lambda_cloud.catalog_rotation_cost_review import (
    load_lambda_catalog_rotation_cost_review,
)
from decodilo.lambda_cloud.catalog_rotation_operator_decision import (
    load_lambda_catalog_rotation_operator_decision,
)
from decodilo.lambda_cloud.catalog_rotation_risk_acceptance import (
    load_lambda_catalog_rotation_risk_acceptance,
)
from decodilo.lambda_cloud.catalog_rotation_shape_authorization import (
    load_lambda_catalog_rotation_shape_authorization,
)
from decodilo.lambda_cloud.catalog_rotation_wait_plan import (
    load_lambda_catalog_rotation_wait_plan,
)
from decodilo.lambda_cloud.m044_decision_record import load_lambda_m044_decision_record


class LambdaM044Report(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    cost_review_passed: bool
    risk_acceptance_status: str
    operator_decision_status: str
    wait_plan_status: str | None = None
    authorization_status: str | None = None
    command_preview_status: str | None = None
    decision_status: str
    selected_candidate: str | None = None
    estimated_30min_cost: float | None = None
    buffered_estimated_30min_cost: float | None = None
    future_review_allowed: bool = False
    report_passed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaM044Report:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M044 report cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m044_report_from_paths(
    *,
    cost_review: str | Path,
    risk_acceptance: str | Path,
    operator_decision: str | Path,
    decision: str | Path,
    authorization: str | Path | None = None,
    command_preview: str | Path | None = None,
    wait_plan: str | Path | None = None,
) -> LambdaM044Report:
    cost = load_lambda_catalog_rotation_cost_review(cost_review)
    risk = load_lambda_catalog_rotation_risk_acceptance(risk_acceptance)
    operator = load_lambda_catalog_rotation_operator_decision(operator_decision)
    record = load_lambda_m044_decision_record(decision)
    auth = (
        None
        if authorization is None or not Path(authorization).exists()
        else load_lambda_catalog_rotation_shape_authorization(authorization)
    )
    preview = (
        None
        if command_preview is None or not Path(command_preview).exists()
        else load_lambda_catalog_rotation_command_preview(command_preview)
    )
    wait = (
        None
        if wait_plan is None or not Path(wait_plan).exists()
        else load_lambda_catalog_rotation_wait_plan(wait_plan)
    )
    blockers = [
        *cost.blockers,
        *risk.blockers,
        *operator.blockers,
        *record.blockers,
    ]
    warnings = [
        "M044 is review-only and cannot launch",
        "future M045 review requires a separate supervised milestone",
        *cost.warnings,
        *risk.warnings,
        *operator.warnings,
        *record.warnings,
    ]
    if auth is not None:
        blockers.extend(auth.blockers)
        warnings.extend(auth.warnings)
    if preview is not None:
        blockers.extend(preview.blockers)
        warnings.extend(preview.warnings)
    if wait is not None:
        blockers.extend(wait.blockers)
        warnings.extend(wait.warnings)
    report_passed = record.decision_status in {
        "authorize_future_m045_catalog_rotation_launch_review",
        "wait_for_live_availability",
        "require_manual_candidate_selection",
    } and not blockers
    return LambdaM044Report(
        cost_review_passed=cost.cost_review_passed,
        risk_acceptance_status=risk.acceptance_status,
        operator_decision_status=operator.decision_status,
        wait_plan_status=None if wait is None else wait.plan_status,
        authorization_status=None if auth is None else auth.authorization_status,
        command_preview_status=None if preview is None else preview.preview_status,
        decision_status=record.decision_status,
        selected_candidate=record.selected_candidate or cost.selected_candidate,
        estimated_30min_cost=cost.estimated_30min_cost,
        buffered_estimated_30min_cost=cost.buffered_estimated_30min_cost,
        future_review_allowed=record.future_review_allowed,
        report_passed=report_passed,
        blockers=sorted(set(blockers)),
        warnings=sorted(set(warnings)),
    )


def load_lambda_m044_report(path: str | Path) -> LambdaM044Report:
    return LambdaM044Report.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_m044_report(path: str | Path, report: LambdaM044Report) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
