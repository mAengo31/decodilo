"""Future-launch decision for lower-cost Strand-compatible review."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.lower_cost_authorization_package import (
    LambdaLowerCostAuthorizationPackage,
    load_lambda_lower_cost_authorization_package,
)

LambdaLowerCostFutureLaunchDecisionStatus = Literal[
    "needs_more_evidence",
    "authorized_for_future_lower_cost_launch_review",
    "blocked",
]


class LambdaLowerCostFutureLaunchDecision(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    decision_status: LambdaLowerCostFutureLaunchDecisionStatus
    future_launch_review_authorized: bool
    immediate_launch_authorized: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaLowerCostFutureLaunchDecision:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.immediate_launch_authorized
        ):
            raise ValueError("lower-cost decision cannot authorize immediate launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_lower_cost_future_launch_decision(
    *,
    authorization_package: LambdaLowerCostAuthorizationPackage,
) -> LambdaLowerCostFutureLaunchDecision:
    authorized = (
        authorization_package.future_authorization_status
        == "authorized_for_future_lower_cost_launch_review"
    )
    blockers = list(authorization_package.blockers)
    status: LambdaLowerCostFutureLaunchDecisionStatus
    if authorized:
        status = "authorized_for_future_lower_cost_launch_review"
    elif blockers:
        status = "blocked"
    else:
        status = "needs_more_evidence"
    return LambdaLowerCostFutureLaunchDecision(
        decision_status=status,
        future_launch_review_authorized=authorized,
        blockers=blockers,
        warnings=[
            "decision is future-review only",
            "operator approval and fresh launch gates remain required before any launch",
        ],
    )


def build_lambda_lower_cost_future_launch_decision_from_path(
    *,
    authorization_package: str | Path,
) -> LambdaLowerCostFutureLaunchDecision:
    return build_lambda_lower_cost_future_launch_decision(
        authorization_package=load_lambda_lower_cost_authorization_package(
            authorization_package
        )
    )


def load_lambda_lower_cost_future_launch_decision(
    path: str | Path,
) -> LambdaLowerCostFutureLaunchDecision:
    return LambdaLowerCostFutureLaunchDecision.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_lower_cost_future_launch_decision(
    path: str | Path,
    report: LambdaLowerCostFutureLaunchDecision,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
