"""Go/no-go decision for future availability-first Lambda launch review."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.availability_first_authorization_package import (
    LambdaAvailabilityFirstAuthorizationPackage,
    load_lambda_availability_first_authorization_package,
)

LambdaAvailabilityFirstGoNoGoStatus = Literal[
    "no_go",
    "needs_more_evidence",
    "go_for_future_availability_first_launch_review",
]


class LambdaAvailabilityFirstGoNoGo(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    status: LambdaAvailabilityFirstGoNoGoStatus
    future_review_allowed: bool
    immediate_launch_authorized: bool = False
    operator_risk_acceptance_required: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaAvailabilityFirstGoNoGo:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.immediate_launch_authorized
        ):
            raise ValueError("availability-first go/no-go cannot authorize execution")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_availability_first_go_no_go(
    authorization: LambdaAvailabilityFirstAuthorizationPackage,
) -> LambdaAvailabilityFirstGoNoGo:
    if (
        authorization.authorization_status
        == "authorized_for_future_availability_first_launch_review"
    ):
        status: LambdaAvailabilityFirstGoNoGoStatus = (
            "go_for_future_availability_first_launch_review"
        )
        blockers: list[str] = []
    elif authorization.blockers:
        status = "needs_more_evidence"
        blockers = authorization.blockers
    else:
        status = "no_go"
        blockers = ["availability_first_authorization_not_passed"]
    return LambdaAvailabilityFirstGoNoGo(
        status=status,
        future_review_allowed=status == "go_for_future_availability_first_launch_review",
        operator_risk_acceptance_required=authorization.operator_risk_acceptance_required,
        blockers=blockers,
        warnings=[
            "go/no-go is for a future milestone only",
            "launch_ready and launch_allowed remain false",
        ],
    )


def build_lambda_availability_first_go_no_go_from_path(
    authorization: str | Path,
) -> LambdaAvailabilityFirstGoNoGo:
    return build_lambda_availability_first_go_no_go(
        load_lambda_availability_first_authorization_package(authorization)
    )


def load_lambda_availability_first_go_no_go(
    path: str | Path,
) -> LambdaAvailabilityFirstGoNoGo:
    return LambdaAvailabilityFirstGoNoGo.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_availability_first_go_no_go(
    path: str | Path,
    report: LambdaAvailabilityFirstGoNoGo,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
