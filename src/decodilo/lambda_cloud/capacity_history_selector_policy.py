"""Conservative policy for capacity-history-aware Lambda selection."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, model_validator


class LambdaCapacityHistorySelectorPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    exclude_recent_capacity_failures: bool = True
    require_fresh_live_availability_for_same_shape_retry: bool = True
    allow_same_shape_retry_with_explicit_acceptance: bool = False
    max_budget: float = 50.0
    max_runtime_minutes: int = 30
    quantity: int = 1
    prefer_single_gpu: bool = True
    prefer_lowest_cost: bool = True
    no_auto_retry: bool = True
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> LambdaCapacityHistorySelectorPolicy:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or not self.no_auto_retry
            or self.quantity != 1
        ):
            raise ValueError("capacity-history selector policy cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_capacity_history_selector_policy(
    *,
    allow_same_shape_retry_with_explicit_acceptance: bool = False,
    max_budget: float = 50.0,
) -> LambdaCapacityHistorySelectorPolicy:
    return LambdaCapacityHistorySelectorPolicy(
        allow_same_shape_retry_with_explicit_acceptance=(
            allow_same_shape_retry_with_explicit_acceptance
        ),
        max_budget=max_budget,
    )


def load_lambda_capacity_history_selector_policy(
    path: str | Path,
) -> LambdaCapacityHistorySelectorPolicy:
    return LambdaCapacityHistorySelectorPolicy.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_capacity_history_selector_policy(
    path: str | Path,
    report: LambdaCapacityHistorySelectorPolicy,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
