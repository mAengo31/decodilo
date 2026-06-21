"""Strategy update after a successful Lambda lifecycle smoke."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.lifecycle_smoke_success_record import (
    load_lambda_lifecycle_smoke_success_record,
)
from decodilo.lambda_cloud.live_region_selection import load_lambda_live_region_selection


class LambdaSuccessfulLaunchStrategyUpdate(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    lifecycle_smoke_successful: bool
    successful_candidate: str | None = None
    successful_region: str | None = None
    strategy_update: list[str] = Field(default_factory=list)
    next_recommended_stage: Literal[
        "test_profile_cleanup",
        "optional_second_lifecycle_smoke_only_if_needed",
        "remote_runtime_bootstrap_planning",
    ] = "test_profile_cleanup"
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_read_only(self) -> LambdaSuccessfulLaunchStrategyUpdate:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("strategy update cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_successful_launch_strategy_update_from_paths(
    *,
    success_record: str | Path,
    live_region_selection: str | Path | None = None,
) -> LambdaSuccessfulLaunchStrategyUpdate:
    success = load_lambda_lifecycle_smoke_success_record(success_record)
    region = (
        None
        if live_region_selection is None or not Path(live_region_selection).exists()
        else load_lambda_live_region_selection(live_region_selection)
    )
    blockers = list(success.blockers)
    if success.status != "lifecycle_smoke_success":
        blockers.append("lifecycle_smoke_not_successful")
    if region is not None and not region.selection_passed:
        blockers.extend(region.blockers)
    return LambdaSuccessfulLaunchStrategyUpdate(
        lifecycle_smoke_successful=not blockers,
        successful_candidate=success.selected_candidate,
        successful_region=success.selected_region,
        strategy_update=[
            "use_live_instance_type_parser",
            "use_live_region_selection",
            "use_canonical_live_shape_id",
            "keep_flexible_selector_for_future_smoke_tests",
            "do_not_hardcode_stale_shape_names",
        ],
        next_recommended_stage="test_profile_cleanup",
        blockers=sorted(set(blockers)),
        warnings=[
            "strategy update is advisory and does not authorize launch",
            "future lifecycle smoke attempts still require supervised approval",
        ],
    )


def load_lambda_successful_launch_strategy_update(
    path: str | Path,
) -> LambdaSuccessfulLaunchStrategyUpdate:
    return LambdaSuccessfulLaunchStrategyUpdate.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_successful_launch_strategy_update(
    path: str | Path,
    report: LambdaSuccessfulLaunchStrategyUpdate,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
