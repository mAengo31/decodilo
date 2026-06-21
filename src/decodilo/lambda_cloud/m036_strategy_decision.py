"""M036 future-launch strategy decision."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.endpoint_confidence_upgrade import (
    LambdaEndpointConfidenceUpgradeReport,
    load_lambda_endpoint_confidence_upgrade_report,
)
from decodilo.lambda_cloud.lower_cost_shape_reauthorization import (
    LambdaLowerCostShapeReauthorization,
    load_lambda_lower_cost_shape_reauthorization,
)

LambdaM036StrategyDecisionStatus = Literal[
    "require_more_support_evidence",
    "endpoint_confirmed_proceed_to_reauthorization",
    "reauthorize_lower_cost_shape_before_next_launch",
    "keep_current_shape_with_operator_risk_acceptance",
    "pause_real_launch_attempts",
]


class LambdaM036StrategyDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    decision_id: str = "lambda-m036-strategy-decision"
    status: LambdaM036StrategyDecisionStatus
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    next_required_steps: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaM036StrategyDecision:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M036 strategy decision cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m036_strategy_decision(
    *,
    endpoint_upgrade: LambdaEndpointConfidenceUpgradeReport,
    lower_cost_shape: LambdaLowerCostShapeReauthorization,
    operator_keeps_current_shape: bool = False,
) -> LambdaM036StrategyDecision:
    blockers: list[str] = []
    if not endpoint_upgrade.upgrade_passed:
        blockers.extend(endpoint_upgrade.blockers or ["endpoint_confidence_not_high"])
        status: LambdaM036StrategyDecisionStatus = "require_more_support_evidence"
        steps = [
            "collect complete support/operator endpoint behavior evidence",
            "rerun endpoint confidence upgrade",
        ]
    elif (
        lower_cost_shape.decision.status == "reauthorize_lower_cost_shape"
        and not operator_keeps_current_shape
    ):
        status = "reauthorize_lower_cost_shape_before_next_launch"
        steps = [
            "regenerate M020/M028/M029 artifacts for the selected lower-cost shape",
            "create a future launch review package after reauthorization",
        ]
    elif operator_keeps_current_shape:
        status = "keep_current_shape_with_operator_risk_acceptance"
        steps = [
            "record operator risk acceptance for current shape",
            "perform future launch review; no immediate execution in M036",
        ]
    else:
        status = "endpoint_confirmed_proceed_to_reauthorization"
        steps = ["prepare future reauthorization package; M036 does not launch"]
    return LambdaM036StrategyDecision(
        status=status,
        blockers=sorted(set(blockers)),
        warnings=[
            "M036 decision is future-review only and cannot authorize immediate launch",
            *endpoint_upgrade.warnings,
            *lower_cost_shape.decision.warnings,
        ],
        next_required_steps=steps,
    )


def build_lambda_m036_missing_support_decision() -> LambdaM036StrategyDecision:
    return LambdaM036StrategyDecision(
        status="require_more_support_evidence",
        blockers=["support_confirmation_response_missing"],
        warnings=["M036 decision is future-review only and cannot authorize immediate launch"],
        next_required_steps=[
            "send the M036 support/operator confirmation request",
            "ingest a real support/operator response",
            "rerun validation and endpoint confidence upgrade",
        ],
    )


def build_lambda_m036_strategy_decision_from_paths(
    *,
    endpoint_confidence_upgrade: str | Path,
    lower_cost_shape_review: str | Path,
    operator_keeps_current_shape: bool = False,
) -> LambdaM036StrategyDecision:
    return build_lambda_m036_strategy_decision(
        endpoint_upgrade=load_lambda_endpoint_confidence_upgrade_report(
            endpoint_confidence_upgrade
        ),
        lower_cost_shape=load_lambda_lower_cost_shape_reauthorization(
            lower_cost_shape_review
        ),
        operator_keeps_current_shape=operator_keeps_current_shape,
    )


def load_lambda_m036_strategy_decision(path: str | Path) -> LambdaM036StrategyDecision:
    return LambdaM036StrategyDecision.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_m036_strategy_decision(
    path: str | Path,
    report: LambdaM036StrategyDecision,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
