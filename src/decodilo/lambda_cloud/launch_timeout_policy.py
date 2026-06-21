"""Launch timeout policy for a future M034 third attempt."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

LambdaTerminateRetryPolicy = Literal["none", "owned_idempotent_single_retry"]


class LambdaLaunchTimeoutPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    policy_id: str = "lambda-m033-launch-timeout-policy"
    launch_request_timeout_seconds: float
    terminate_request_timeout_seconds: float
    read_only_verification_timeout_seconds: float
    poll_interval_seconds: float = 5.0
    max_read_only_reconcile_seconds: float = 120.0
    no_auto_launch_retry: bool = True
    terminate_retry_policy: LambdaTerminateRetryPolicy = "owned_idempotent_single_retry"
    manual_review_on_unknown: bool = True
    policy_passed: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> LambdaLaunchTimeoutPolicy:
        if self.launch_ready or self.launch_allowed:
            raise ValueError("launch timeout policy cannot enable launch")
        if self.policy_passed and self.blockers:
            raise ValueError("launch timeout policy cannot pass with blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_launch_timeout_policy(
    *,
    launch_request_timeout_seconds: float = 30.0,
    terminate_request_timeout_seconds: float = 30.0,
    read_only_verification_timeout_seconds: float = 120.0,
    poll_interval_seconds: float = 5.0,
    max_read_only_reconcile_seconds: float = 120.0,
    no_auto_launch_retry: bool = True,
    terminate_retry_policy: LambdaTerminateRetryPolicy = "owned_idempotent_single_retry",
    manual_review_on_unknown: bool = True,
) -> LambdaLaunchTimeoutPolicy:
    blockers: list[str] = []
    warnings: list[str] = []
    values = {
        "launch_request_timeout_seconds": launch_request_timeout_seconds,
        "terminate_request_timeout_seconds": terminate_request_timeout_seconds,
        "read_only_verification_timeout_seconds": read_only_verification_timeout_seconds,
        "poll_interval_seconds": poll_interval_seconds,
        "max_read_only_reconcile_seconds": max_read_only_reconcile_seconds,
    }
    blockers.extend(name for name, value in values.items() if value <= 0)
    if launch_request_timeout_seconds < 5.0:
        blockers.append("launch_timeout_too_low_for_prior_response_loss")
    if terminate_request_timeout_seconds < 5.0:
        blockers.append("terminate_timeout_too_low")
    if read_only_verification_timeout_seconds < terminate_request_timeout_seconds:
        blockers.append("read_only_verification_timeout_too_low")
    if not no_auto_launch_retry:
        blockers.append("automatic_launch_retry_allowed")
    if not manual_review_on_unknown:
        blockers.append("manual_review_on_unknown_disabled")
    if launch_request_timeout_seconds < 30.0:
        warnings.append("launch timeout is below recommended 30 seconds")
    return LambdaLaunchTimeoutPolicy(
        launch_request_timeout_seconds=launch_request_timeout_seconds,
        terminate_request_timeout_seconds=terminate_request_timeout_seconds,
        read_only_verification_timeout_seconds=read_only_verification_timeout_seconds,
        poll_interval_seconds=poll_interval_seconds,
        max_read_only_reconcile_seconds=max_read_only_reconcile_seconds,
        no_auto_launch_retry=no_auto_launch_retry,
        terminate_retry_policy=terminate_retry_policy,
        manual_review_on_unknown=manual_review_on_unknown,
        policy_passed=not blockers,
        blockers=blockers,
        warnings=warnings,
    )


def load_lambda_launch_timeout_policy(path: str | Path) -> LambdaLaunchTimeoutPolicy:
    return LambdaLaunchTimeoutPolicy.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_launch_timeout_policy(
    path: str | Path,
    policy: LambdaLaunchTimeoutPolicy,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(policy.to_json(), encoding="utf-8")
