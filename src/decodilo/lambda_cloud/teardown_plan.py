"""Dry-run-only Lambda teardown plan."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.errors import LaunchDisabledError


class LambdaTeardownPlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    plan_schema_version: int = 1
    run_id: str
    resources_to_terminate: list[str] = Field(default_factory=list)
    terminate_order: list[str] = Field(default_factory=list)
    verification_steps: list[str] = Field(default_factory=list)
    max_teardown_wait_seconds: int = Field(default=0, ge=0)
    orphan_detection_enabled: bool = True
    teardown_enabled: bool = False
    live_resource_ids: list[str] = Field(default_factory=list)
    reason_teardown_disabled: str = "M018 is offline only; Lambda teardown is disabled"

    @model_validator(mode="after")
    def _validate_disabled(self) -> LambdaTeardownPlan:
        if self.teardown_enabled:
            raise ValueError("Lambda teardown must remain disabled in M018")
        if self.live_resource_ids:
            raise ValueError("M018 Lambda teardown plan must not contain live resource IDs")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_teardown_plan(*, run_id: str, planned_node_ids: list[str]) -> LambdaTeardownPlan:
    return LambdaTeardownPlan(
        run_id=run_id,
        resources_to_terminate=planned_node_ids,
        terminate_order=planned_node_ids,
        verification_steps=[
            "future launcher records live Lambda resource identifiers before launch",
            "future launcher verifies provider-side termination",
            "M018 does not terminate anything",
        ],
        max_teardown_wait_seconds=0,
    )


def execute_lambda_teardown_plan(plan: LambdaTeardownPlan) -> None:
    raise LaunchDisabledError(
        f"Lambda teardown execution is disabled for {plan.run_id}; no live resources exist"
    )


def load_lambda_teardown_plan(path: str | Path) -> LambdaTeardownPlan:
    return LambdaTeardownPlan.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_teardown_plan(path: str | Path, plan: LambdaTeardownPlan) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(plan.to_json(), encoding="utf-8")
