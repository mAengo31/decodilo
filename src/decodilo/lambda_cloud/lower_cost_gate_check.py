"""Gate check for the lower-cost future M039 launch review."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.lower_cost_canonical_readiness import (
    LambdaLowerCostCanonicalReadinessReport,
    load_lambda_lower_cost_canonical_readiness,
)
from decodilo.lambda_cloud.lower_cost_m039_authorization import (
    LambdaLowerCostM039Authorization,
    load_lambda_lower_cost_m039_authorization,
)
from decodilo.lambda_cloud.strand_response_loss_control_check import (
    LambdaStrandResponseLossControlCheck,
    load_lambda_strand_response_loss_control_check,
)


class LambdaLowerCostGateCheck(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    gate_passed: bool
    effective_launch_timeout_seconds: float | None
    response_capture_active: bool
    status_before_parse: bool
    no_auto_launch_retry: bool
    strand_payload_compatible: bool
    selected_shape: str
    selected_ssh_key_hash: str | None = None
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaLowerCostGateCheck:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("lower-cost gate check cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_lower_cost_gate_check(
    *,
    authorization: LambdaLowerCostM039Authorization,
    canonical_readiness: LambdaLowerCostCanonicalReadinessReport,
    response_loss_controls: LambdaStrandResponseLossControlCheck,
) -> LambdaLowerCostGateCheck:
    blockers: list[str] = []
    if (
        authorization.authorization_status
        != "authorized_for_future_m039_lower_cost_launch_attempt"
    ):
        blockers.extend(authorization.blockers or ["m039_authorization_not_passed"])
    if not canonical_readiness.readiness_passed:
        blockers.extend(canonical_readiness.blockers or ["canonical_readiness_failed"])
    if not response_loss_controls.controls_passed:
        blockers.extend(response_loss_controls.blockers or ["response_loss_controls_failed"])
    return LambdaLowerCostGateCheck(
        gate_passed=not blockers,
        effective_launch_timeout_seconds=response_loss_controls.timeout_seconds,
        response_capture_active=response_loss_controls.response_capture_active,
        status_before_parse=response_loss_controls.status_before_parse,
        no_auto_launch_retry=response_loss_controls.no_auto_launch_retry,
        strand_payload_compatible=canonical_readiness.strand_payload_compatible,
        selected_shape=canonical_readiness.shape,
        selected_ssh_key_hash=canonical_readiness.selected_ssh_key_hash,
        blockers=sorted(set(blockers)),
        warnings=["lower-cost gate check is future-review only"],
    )


def build_lambda_lower_cost_gate_check_from_paths(
    *,
    authorization: str | Path,
    canonical_readiness: str | Path,
    response_loss_controls: str | Path,
) -> LambdaLowerCostGateCheck:
    return build_lambda_lower_cost_gate_check(
        authorization=load_lambda_lower_cost_m039_authorization(authorization),
        canonical_readiness=load_lambda_lower_cost_canonical_readiness(
            canonical_readiness
        ),
        response_loss_controls=load_lambda_strand_response_loss_control_check(
            response_loss_controls
        ),
    )


def load_lambda_lower_cost_gate_check(path: str | Path) -> LambdaLowerCostGateCheck:
    return LambdaLowerCostGateCheck.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_lower_cost_gate_check(
    path: str | Path,
    report: LambdaLowerCostGateCheck,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
