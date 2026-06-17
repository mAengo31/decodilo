"""Typed cloud dry-run plan models."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CloudSafetyCheck(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    passed: bool
    reason: str = ""


class CloudNodePlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    node_id: str
    provider: str
    shape: str
    gpu_type: str
    gpus_per_instance: int = Field(gt=0)
    region: str | None = None


class CloudLaunchPlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    provider: str
    mode: str = "cloud-dry-run"
    region: str | None = None
    node_count: int = Field(gt=0)
    instance_type: str
    gpu_type: str
    gpus_per_instance: int = Field(gt=0)
    total_gpus: int = Field(gt=0)
    planned_hours: float = Field(gt=0)
    price_snapshot_id: str
    selected_price_record_id: str
    base_estimated_cost: float = Field(ge=0)
    safety_buffer_adjusted_cost: float = Field(ge=0)
    max_run_budget: float = Field(ge=0)
    starting_credits: float = Field(ge=0)
    projected_remaining_credits: float
    run_spec_hash: str | None = None
    artifact_manifest_path: str | None = None
    launch_review_checklist_path: str | None = None
    ssh_required: bool = True
    secrets_required: list[str] = Field(default_factory=list)
    startup_commands: list[str] = Field(default_factory=list)
    teardown_commands: list[str] = Field(default_factory=list)
    teardown_plan: dict[str, Any] | None = None
    nodes: list[CloudNodePlan] = Field(default_factory=list)
    safety_checks: list[CloudSafetyCheck] = Field(default_factory=list)
    launch_allowed: bool = False
    reason_launch_not_allowed: str = "This scaffold is dry-run only; launch is disabled."
    budget_manifest: dict[str, Any] | None = None
    capacity_plan: dict[str, Any] | None = None
    trainer_type: str | None = None
    expected_trainer_state_bytes: int | None = Field(default=None, gt=0)
    expected_model_parameter_count: int | None = Field(default=None, gt=0)
    warnings: list[str] = Field(default_factory=list)


class CloudRunPlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    launch_plan: CloudLaunchPlan


class CloudDryRunReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    plan: CloudLaunchPlan
    validation_errors: list[str] = Field(default_factory=list)

    @property
    def launch_allowed(self) -> bool:
        return self.plan.launch_allowed

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def write_cloud_dry_run_report(path: str | Path, report: CloudDryRunReport) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")


def load_cloud_dry_run_report(path: str | Path) -> CloudDryRunReport:
    return CloudDryRunReport.model_validate_json(Path(path).read_text(encoding="utf-8"))
