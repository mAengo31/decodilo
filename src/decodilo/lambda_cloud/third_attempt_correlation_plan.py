"""Correlation plan for a future M034 third Lambda launch attempt."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.launch_timeout_policy import (
    LambdaLaunchTimeoutPolicy,
    load_lambda_launch_timeout_policy,
)
from decodilo.lambda_cloud.m029_launch_authorization import (
    LambdaM029AuthorizationPackage,
    load_lambda_m029_authorization_package,
)
from decodilo.lambda_cloud.real_launch_idempotency import build_m029_idempotency_report
from decodilo.lambda_cloud.response_capture_settings_lock import (
    LambdaResponseCaptureSettingsLock,
    load_lambda_response_capture_settings_lock,
)


class LambdaThirdAttemptCorrelationPlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    prior_attempt_ids: list[str] = Field(default_factory=list)
    third_attempt_id: str
    idempotency_key: str
    prior_idempotency_keys: list[str] = Field(default_factory=list)
    request_hash: str
    planned_shape: str
    planned_region: str
    planned_image: str | None = None
    pre_launch_discovery_ref: str
    response_capture_settings_lock_hash: str
    timeout_policy_id: str
    no_automatic_retry: bool = True
    candidate_matching_rules: list[str] = Field(default_factory=list)
    manual_review_trigger: str
    plan_passed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> LambdaThirdAttemptCorrelationPlan:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("third-attempt correlation plan cannot enable launch")
        if self.idempotency_key in self.prior_idempotency_keys:
            raise ValueError("third-attempt idempotency key must differ from prior attempts")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_third_attempt_correlation_plan(
    *,
    m029_authorization: LambdaM029AuthorizationPackage,
    response_capture_lock: LambdaResponseCaptureSettingsLock,
    timeout_policy: LambdaLaunchTimeoutPolicy,
    third_attempt_id: str = "lambda-m034-third-launch-review",
    prior_attempt_ids: list[str] | None = None,
    prior_idempotency_keys: list[str] | None = None,
    pre_launch_discovery_ref: str = "required-immediately-before-m034-request",
) -> LambdaThirdAttemptCorrelationPlan:
    launch_auth = m029_authorization.launch_authorization
    idempotency = build_m029_idempotency_report(
        run_id=third_attempt_id,
        plan_hash=f"{launch_auth.authorization_id}:third-attempt",
    )
    prior_keys = prior_idempotency_keys or [
        "m029-launch-one-instance",
        "m031-launch-one-instance",
    ]
    material = {
        "attempt_id": third_attempt_id,
        "planned_shape": launch_auth.planned_instance_type,
        "planned_region": launch_auth.planned_region,
        "planned_image": launch_auth.image_ref,
        "capture_lock": response_capture_lock.lock_hash,
        "timeout_policy": timeout_policy.policy_id,
    }
    blockers: list[str] = []
    if idempotency.launch_key.idempotency_key in prior_keys:
        blockers.append("third_attempt_idempotency_key_reused")
    if not launch_auth.planned_instance_type:
        blockers.append("planned_shape_missing")
    if not launch_auth.planned_region:
        blockers.append("planned_region_missing")
    if not response_capture_lock.lock_passed:
        blockers.append("response_capture_lock_failed")
    if not timeout_policy.policy_passed:
        blockers.append("timeout_policy_failed")
    if not timeout_policy.no_auto_launch_retry:
        blockers.append("automatic_launch_retry_allowed")
    return LambdaThirdAttemptCorrelationPlan(
        prior_attempt_ids=prior_attempt_ids or ["M029C", "M031"],
        third_attempt_id=third_attempt_id,
        idempotency_key=idempotency.launch_key.idempotency_key,
        prior_idempotency_keys=prior_keys,
        request_hash=hashlib.sha256(
            json.dumps(material, sort_keys=True).encode("utf-8")
        ).hexdigest(),
        planned_shape=launch_auth.planned_instance_type,
        planned_region=launch_auth.planned_region,
        planned_image=launch_auth.image_ref,
        pre_launch_discovery_ref=pre_launch_discovery_ref,
        response_capture_settings_lock_hash=response_capture_lock.lock_hash,
        timeout_policy_id=timeout_policy.policy_id,
        no_automatic_retry=timeout_policy.no_auto_launch_retry,
        candidate_matching_rules=[
            "match exact owned id from response when present",
            "match planned shape and region",
            "match launch timestamp window when exposed",
            "capture status and redacted response metadata before parsing",
            "require exact or high-confidence ownership before termination",
        ],
        manual_review_trigger="response loss, ambiguous candidate, or low ownership confidence",
        plan_passed=not blockers,
        blockers=blockers,
        warnings=["M033 correlation plan is review-only and cannot launch"],
    )


def build_lambda_third_attempt_correlation_plan_from_paths(
    *,
    m029_authorization: str | Path,
    response_capture_lock: str | Path,
    timeout_policy: str | Path,
) -> LambdaThirdAttemptCorrelationPlan:
    return build_lambda_third_attempt_correlation_plan(
        m029_authorization=load_lambda_m029_authorization_package(m029_authorization),
        response_capture_lock=load_lambda_response_capture_settings_lock(
            response_capture_lock
        ),
        timeout_policy=load_lambda_launch_timeout_policy(timeout_policy),
    )


def load_lambda_third_attempt_correlation_plan(
    path: str | Path,
) -> LambdaThirdAttemptCorrelationPlan:
    return LambdaThirdAttemptCorrelationPlan.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_third_attempt_correlation_plan(
    path: str | Path,
    plan: LambdaThirdAttemptCorrelationPlan,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(plan.to_json(), encoding="utf-8")
