"""Correlation plan for a future second Lambda launch attempt."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.m029_launch_authorization import (
    LambdaM029AuthorizationPackage,
    load_lambda_m029_authorization_package,
)
from decodilo.lambda_cloud.m029_report import LambdaM029Report, load_lambda_m029_report
from decodilo.lambda_cloud.real_launch_idempotency import build_m029_idempotency_report


class LambdaSecondAttemptCorrelationPlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    prior_attempt_id: str
    second_attempt_id: str
    idempotency_key: str
    prior_idempotency_key: str
    request_hash: str
    planned_shape: str
    planned_region: str
    planned_image: str | None = None
    pre_launch_discovery_ref: str
    launch_window: str
    response_loss_policy: str
    candidate_matching_rules: list[str] = Field(default_factory=list)
    manual_review_trigger: str
    plan_passed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_plan(self) -> LambdaSecondAttemptCorrelationPlan:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("second-attempt correlation plan cannot enable launch")
        if self.idempotency_key == self.prior_idempotency_key:
            raise ValueError("second attempt idempotency key must differ from prior attempt")
        if not self.planned_shape or not self.planned_region:
            raise ValueError("planned shape and region are required")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_second_attempt_correlation_plan(
    *,
    prior_m029_report: LambdaM029Report,
    m029_authorization: LambdaM029AuthorizationPackage,
    second_attempt_id: str = "lambda-m031-second-launch-review",
    prior_idempotency_key: str = "m029-launch-one-instance",
    pre_launch_discovery_ref: str = "required-immediately-before-m031-request",
) -> LambdaSecondAttemptCorrelationPlan:
    launch_auth = m029_authorization.launch_authorization
    idempotency = build_m029_idempotency_report(
        run_id=second_attempt_id,
        plan_hash=f"{launch_auth.authorization_id}:second-attempt",
    )
    planned_shape = launch_auth.planned_instance_type
    planned_region = launch_auth.planned_region
    request_material = {
        "attempt_id": second_attempt_id,
        "planned_shape": planned_shape,
        "planned_region": planned_region,
        "planned_image": launch_auth.image_ref,
        "prior_attempt_id": prior_m029_report.run_id,
    }
    blockers: list[str] = []
    if idempotency.launch_key.idempotency_key == prior_idempotency_key:
        blockers.append("second_attempt_idempotency_key_reused")
    if not planned_shape:
        blockers.append("planned_shape_missing")
    if not planned_region:
        blockers.append("planned_region_missing")
    return LambdaSecondAttemptCorrelationPlan(
        prior_attempt_id=prior_m029_report.run_id,
        second_attempt_id=second_attempt_id,
        idempotency_key=idempotency.launch_key.idempotency_key,
        prior_idempotency_key=prior_idempotency_key,
        request_hash=hashlib.sha256(
            json.dumps(request_material, sort_keys=True).encode("utf-8")
        ).hexdigest(),
        planned_shape=planned_shape,
        planned_region=planned_region,
        planned_image=launch_auth.image_ref,
        pre_launch_discovery_ref=pre_launch_discovery_ref,
        launch_window="operator-supervised-window-required",
        response_loss_policy="no automatic retry; reconcile by read-only discovery",
        candidate_matching_rules=[
            "match planned shape",
            "match planned region",
            "match launch timestamp window when provider exposes it",
            "require exact or high-confidence ownership before termination",
        ],
        manual_review_trigger="missing response, ambiguous candidate, or low ownership confidence",
        plan_passed=not blockers,
        blockers=blockers,
        warnings=["M030 correlation plan is review-only and cannot launch"],
    )


def build_lambda_second_attempt_correlation_plan_from_paths(
    *,
    prior_m029_report: str | Path,
    m029_authorization: str | Path,
) -> LambdaSecondAttemptCorrelationPlan:
    return build_lambda_second_attempt_correlation_plan(
        prior_m029_report=load_lambda_m029_report(prior_m029_report),
        m029_authorization=load_lambda_m029_authorization_package(m029_authorization),
    )


def load_lambda_second_attempt_correlation_plan(
    path: str | Path,
) -> LambdaSecondAttemptCorrelationPlan:
    return LambdaSecondAttemptCorrelationPlan.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_second_attempt_correlation_plan(
    path: str | Path,
    plan: LambdaSecondAttemptCorrelationPlan,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(plan.to_json(), encoding="utf-8")
