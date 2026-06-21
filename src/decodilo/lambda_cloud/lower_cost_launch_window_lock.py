"""Launch-window lock for the future lower-cost M039 milestone."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LambdaLowerCostLaunchWindowLock(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    max_runtime_minutes: int
    operator_required: bool = True
    background_execution: bool = False
    max_launch_attempts: int = 1
    no_auto_launch_retry: bool = True
    launch_window_lock_passed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaLowerCostLaunchWindowLock:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("lower-cost launch window lock cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_lower_cost_launch_window_lock(
    *,
    max_runtime_minutes: int = 30,
    operator_required: bool = True,
    background_execution: bool = False,
    max_launch_attempts: int = 1,
    no_auto_launch_retry: bool = True,
) -> LambdaLowerCostLaunchWindowLock:
    blockers: list[str] = []
    if max_runtime_minutes > 30:
        blockers.append("max_runtime_exceeds_30_minutes")
    if not operator_required:
        blockers.append("operator_presence_required")
    if background_execution:
        blockers.append("background_execution_forbidden")
    if max_launch_attempts != 1:
        blockers.append("max_launch_attempts_must_equal_one")
    if not no_auto_launch_retry:
        blockers.append("automatic_launch_retry_forbidden")
    return LambdaLowerCostLaunchWindowLock(
        max_runtime_minutes=max_runtime_minutes,
        operator_required=operator_required,
        background_execution=background_execution,
        max_launch_attempts=max_launch_attempts,
        no_auto_launch_retry=no_auto_launch_retry,
        launch_window_lock_passed=not blockers,
        blockers=blockers,
        warnings=["launch window lock is future M039 review only"],
    )


def load_lambda_lower_cost_launch_window_lock(
    path: str | Path,
) -> LambdaLowerCostLaunchWindowLock:
    return LambdaLowerCostLaunchWindowLock.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_lower_cost_launch_window_lock(
    path: str | Path,
    report: LambdaLowerCostLaunchWindowLock,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
