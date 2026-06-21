"""Future M054B SSH-connectivity-only execution plan."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.m054_ssh_connectivity_authorization import (
    load_lambda_m054_ssh_connectivity_authorization,
)

LambdaSSHConnectivityExecutionPlanStatus = Literal["plan_defined", "blocked"]


class LambdaSSHConnectivityExecutionPlanReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    plan_schema_version: int = 1
    target_milestone: str = "M054B"
    mode: str = "ssh_connectivity_only"
    plan_status: LambdaSSHConnectivityExecutionPlanStatus
    launch_required: bool = True
    max_instances: int = 1
    max_runtime_minutes: int = 30
    max_budget: float = 50.0
    selected_candidate_source: str = "future fresh metadata plan / selector"
    ssh_connectivity_probe_enabled_for_future: bool = True
    remote_exec_allowed: bool = False
    interactive_shell_allowed: bool = False
    file_transfer_allowed: bool = False
    port_forwarding_allowed: bool = False
    package_install_allowed: bool = False
    training_allowed: bool = False
    setup_scripts_allowed: bool = False
    cloud_init_allowed: bool = False
    background_execution_allowed: bool = False
    unattended_execution_allowed: bool = False
    owned_instance_termination_required: bool = True
    termination_verification_required: bool = True
    authorization_status: str
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_plan(self) -> LambdaSSHConnectivityExecutionPlanReport:
        forbidden_enabled = (
            self.remote_exec_allowed
            or self.interactive_shell_allowed
            or self.file_transfer_allowed
            or self.port_forwarding_allowed
            or self.package_install_allowed
            or self.training_allowed
            or self.setup_scripts_allowed
            or self.cloud_init_allowed
            or self.background_execution_allowed
            or self.unattended_execution_allowed
        )
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or forbidden_enabled
            or self.max_instances != 1
            or self.max_runtime_minutes > 30
            or self.max_budget > 50
            or not self.owned_instance_termination_required
            or not self.termination_verification_required
        ):
            raise ValueError("M054A execution plan cannot enable unsafe execution")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


LambdaSSHConnectivityExecutionPlan = LambdaSSHConnectivityExecutionPlanReport


def build_lambda_ssh_connectivity_execution_plan_from_path(
    authorization: str | Path,
) -> LambdaSSHConnectivityExecutionPlanReport:
    auth = load_lambda_m054_ssh_connectivity_authorization(authorization)
    blockers = list(auth.blockers)
    if auth.authorization_status != "authorized_for_future_m054_ssh_connectivity_review":
        blockers.append("m054_ssh_connectivity_authorization_required")
    return LambdaSSHConnectivityExecutionPlanReport(
        plan_status="plan_defined" if not blockers else "blocked",
        authorization_status=auth.authorization_status,
        blockers=sorted(set(blockers)),
        warnings=[
            "M054A defines future SSH connectivity only; it does not launch or SSH",
            "M054B must still run under one-shot supervised lifecycle controls",
            *auth.warnings,
        ],
    )


def load_lambda_ssh_connectivity_execution_plan(
    path: str | Path,
) -> LambdaSSHConnectivityExecutionPlanReport:
    return LambdaSSHConnectivityExecutionPlanReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_ssh_connectivity_execution_plan(
    path: str | Path,
    report: LambdaSSHConnectivityExecutionPlanReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
