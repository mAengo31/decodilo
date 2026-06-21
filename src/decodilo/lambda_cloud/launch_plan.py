"""Dry-run-only Lambda launch plan models."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.errors import LaunchDisabledError
from decodilo.lambda_cloud.safety import default_lambda_safety_gate


class LambdaNodePlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    node_id: str
    instance_type: str
    region: str
    image: str | None = None
    gpus_per_instance: int = Field(gt=0)


class LambdaLaunchPlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    plan_schema_version: int = 1
    run_id: str
    provider: str = "lambda"
    mode: str = "lambda-dry-run"
    node_count: int = Field(gt=0)
    instance_type: str
    region: str
    image: str | None = None
    ssh_key_ref: str | None = None
    filesystem_refs: list[str] = Field(default_factory=list)
    planned_hours: float = Field(gt=0)
    max_runtime_minutes: int = Field(gt=0)
    max_run_budget: float = Field(ge=0)
    price_snapshot_ref: str | None = None
    budget_manifest_ref: str | None = None
    resource_ledger_ref: str | None = None
    nodes: list[LambdaNodePlan] = Field(default_factory=list)
    launch_enabled: bool = False
    launch_allowed: bool = False
    reason_launch_disabled: str = "M018 is offline only; Lambda launch is disabled"
    safety_gate: dict = Field(default_factory=lambda: default_lambda_safety_gate().model_dump())

    @model_validator(mode="after")
    def _validate_disabled(self) -> LambdaLaunchPlan:
        if self.launch_enabled or self.launch_allowed:
            raise ValueError("Lambda launch must remain disabled in M018")
        if self.nodes and len(self.nodes) != self.node_count:
            raise ValueError("node_count must match nodes length")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_launch_plan(
    *,
    run_id: str,
    instance_type: str,
    region: str,
    nodes: int,
    gpus_per_instance: int,
    hours: float,
    max_run_budget: float,
    image: str | None = None,
    ssh_key_ref: str | None = None,
    filesystem_refs: list[str] | None = None,
    price_snapshot_ref: str | None = None,
) -> LambdaLaunchPlan:
    return LambdaLaunchPlan(
        run_id=run_id,
        node_count=nodes,
        instance_type=instance_type,
        region=region,
        image=image,
        ssh_key_ref=ssh_key_ref,
        filesystem_refs=filesystem_refs or [],
        planned_hours=hours,
        max_runtime_minutes=max(1, int(hours * 60)),
        max_run_budget=max_run_budget,
        price_snapshot_ref=price_snapshot_ref,
        nodes=[
            LambdaNodePlan(
                node_id=f"lambda-dry-run-node-{index}",
                instance_type=instance_type,
                region=region,
                image=image,
                gpus_per_instance=gpus_per_instance,
            )
            for index in range(nodes)
        ],
    )


def execute_lambda_launch_plan(plan: LambdaLaunchPlan) -> None:
    raise LaunchDisabledError(
        f"Lambda launch execution is disabled for {plan.run_id}; plan is dry-run only"
    )


def load_lambda_launch_plan(path: str | Path) -> LambdaLaunchPlan:
    return LambdaLaunchPlan.model_validate_json(Path(path).read_text(encoding="utf-8"))


def write_lambda_launch_plan(path: str | Path, plan: LambdaLaunchPlan) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(plan.to_json(), encoding="utf-8")
