"""M040 capacity closeout and availability-first strategy report."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.availability_first_authorization_package import (
    load_lambda_availability_first_authorization_package,
)
from decodilo.lambda_cloud.availability_first_go_no_go import (
    load_lambda_availability_first_go_no_go,
)
from decodilo.lambda_cloud.capacity_error_closeout import (
    load_lambda_capacity_error_closeout,
)


class LambdaM040Report(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    capacity_closeout_status: str
    capacity_closeout_succeeded: bool
    same_shape_retry_blocked: bool
    future_availability_first_required: bool
    availability_authorization_status: str
    go_no_go_status: str
    operator_risk_acceptance_required: bool
    report_passed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaM040Report:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M040 report cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m040_report_from_paths(
    *,
    capacity_closeout: str | Path,
    availability_authorization: str | Path,
    go_no_go: str | Path,
) -> LambdaM040Report:
    closeout = load_lambda_capacity_error_closeout(capacity_closeout)
    authorization = load_lambda_availability_first_authorization_package(
        availability_authorization
    )
    decision = load_lambda_availability_first_go_no_go(go_no_go)
    blockers = [
        *closeout.blockers,
        *authorization.blockers,
        *decision.blockers,
    ]
    return LambdaM040Report(
        capacity_closeout_status=closeout.closeout_status,
        capacity_closeout_succeeded=closeout.closeout_succeeded,
        same_shape_retry_blocked=closeout.future_launch_blocked_for_same_shape,
        future_availability_first_required=closeout.future_availability_first_required,
        availability_authorization_status=authorization.authorization_status,
        go_no_go_status=decision.status,
        operator_risk_acceptance_required=decision.operator_risk_acceptance_required,
        report_passed=not blockers,
        blockers=sorted(set(blockers)),
        warnings=[
            "M040 is review-only and does not authorize launch execution",
            "future availability-first launch still requires a separately supervised milestone",
        ],
    )


def load_lambda_m040_report(path: str | Path) -> LambdaM040Report:
    return LambdaM040Report.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_m040_report(path: str | Path, report: LambdaM040Report) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
