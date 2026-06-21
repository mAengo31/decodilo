"""Strand-compatible lower-cost Lambda launch plan for future review."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.strand_cli_request_shapes import validate_strand_launch_payload
from decodilo.lambda_cloud.strand_ssh_key_selection import (
    LambdaExistingSSHKeySelectionReport,
    load_lambda_existing_ssh_key_selection,
)


class LambdaStrandLowerCostLaunchPlan(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    provider: Literal["lambda"] = "lambda"
    compatibility_profile: Literal["strand_cli"] = "strand_cli"
    source_is_official: bool = False
    source_is_behavioral_evidence: bool = True
    shape: Literal["gpu_1x_h100_pcie"] = "gpu_1x_h100_pcie"
    gpu_type: Literal["H100 PCIe"] = "H100 PCIe"
    gpus_per_instance: Literal[1] = 1
    region: str = "us-west-1"
    quantity: Literal[1] = 1
    region_name: str
    instance_type_name: Literal["gpu_1x_h100_pcie"] = "gpu_1x_h100_pcie"
    ssh_key_names: list[str] = Field(min_length=1)
    file_system_names: list[str] = Field(default_factory=list)
    name: str | None = None
    setup_scripts_allowed: bool = False
    cloud_init_allowed: bool = False
    ssh_allowed: bool = False
    training_allowed: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_strand_plan(self) -> LambdaStrandLowerCostLaunchPlan:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.setup_scripts_allowed
            or self.cloud_init_allowed
            or self.ssh_allowed
            or self.training_allowed
        ):
            raise ValueError("Strand lower-cost launch plan cannot enable execution")
        validate_strand_launch_payload(self.to_strand_payload())
        return self

    def to_strand_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "region_name": self.region_name,
            "instance_type_name": self.instance_type_name,
            "ssh_key_names": self.ssh_key_names,
            "quantity": self.quantity,
        }
        if self.name:
            payload["name"] = self.name
        if self.file_system_names:
            payload["file_system_names"] = self.file_system_names
        return payload


class LambdaStrandLowerCostLaunchPlanReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    plan: LambdaStrandLowerCostLaunchPlan | None = None
    plan_passed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_review_only(self) -> LambdaStrandLowerCostLaunchPlanReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("Strand lower-cost launch plan report cannot enable launch")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_strand_lower_cost_launch_plan(
    *,
    ssh_key_selection: LambdaExistingSSHKeySelectionReport,
    region: str = "us-west-1",
    name: str | None = None,
) -> LambdaStrandLowerCostLaunchPlanReport:
    blockers: list[str] = []
    if not ssh_key_selection.selection_passed:
        blockers.extend(ssh_key_selection.errors or ["existing_ssh_key_selection_failed"])
    key_name = ssh_key_selection.selected_ssh_key_name_for_payload
    if not key_name:
        blockers.append("existing_ssh_key_name_required_for_strand_launch")
    plan = None
    if not blockers:
        plan = LambdaStrandLowerCostLaunchPlan(
            region=region,
            region_name=region,
            ssh_key_names=[str(key_name)],
            name=name,
        )
    return LambdaStrandLowerCostLaunchPlanReport(
        plan=plan,
        plan_passed=not blockers,
        blockers=blockers,
        warnings=[
            "Strand lower-cost launch plan is future-review only",
            "no setup scripts, cloud-init, SSH, or training are allowed",
        ],
    )


def build_lambda_strand_lower_cost_launch_plan_from_path(
    *,
    ssh_key_selection: str | Path,
    region: str = "us-west-1",
    name: str | None = None,
) -> LambdaStrandLowerCostLaunchPlanReport:
    return build_lambda_strand_lower_cost_launch_plan(
        ssh_key_selection=load_lambda_existing_ssh_key_selection(ssh_key_selection),
        region=region,
        name=name,
    )


def load_lambda_strand_lower_cost_launch_plan_report(
    path: str | Path,
) -> LambdaStrandLowerCostLaunchPlanReport:
    return LambdaStrandLowerCostLaunchPlanReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_strand_lower_cost_launch_plan_report(
    path: str | Path,
    report: LambdaStrandLowerCostLaunchPlanReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
