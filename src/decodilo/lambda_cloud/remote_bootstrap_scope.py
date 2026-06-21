"""Future-only scope for the first remote Lambda runtime bootstrap review."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

LambdaRemoteBootstrapExperimentType = Literal[
    "lifecycle_plus_metadata_only",
    "lifecycle_plus_ssh_connectivity_check",
    "lifecycle_plus_single_benign_command",
]


class LambdaRemoteBootstrapScopeReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    bootstrap_scope_status: Literal["scoped_for_future_m051_review", "blocked"]
    default_experiment_type: LambdaRemoteBootstrapExperimentType
    allowed_future_experiment_types: list[LambdaRemoteBootstrapExperimentType]
    forbidden_actions: list[str] = Field(default_factory=list)
    required_operator_approval_items: list[str] = Field(default_factory=list)
    max_instances: int = 1
    max_runtime_minutes: int = 30
    owned_instance_termination_required: bool = True
    termination_verification_required: bool = True
    package_install_allowed: bool = False
    training_allowed: bool = False
    setup_scripts_allowed: bool = False
    cloud_init_allowed: bool = False
    unattended_execution_allowed: bool = False
    background_execution_allowed: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_future_only(self) -> LambdaRemoteBootstrapScopeReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.package_install_allowed
            or self.training_allowed
            or self.setup_scripts_allowed
            or self.cloud_init_allowed
            or self.unattended_execution_allowed
            or self.background_execution_allowed
        ):
            raise ValueError("remote bootstrap scope cannot enable launch or runtime work")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


LambdaRemoteBootstrapScope = LambdaRemoteBootstrapScopeReport


def build_lambda_remote_bootstrap_scope(
    *,
    default_experiment_type: LambdaRemoteBootstrapExperimentType = "lifecycle_plus_metadata_only",
) -> LambdaRemoteBootstrapScopeReport:
    forbidden_actions = [
        "training",
        "multi_node",
        "long_running_service",
        "package_installation",
        "git_clone",
        "docker_pull",
        "data_download",
        "model_download",
        "background_process",
        "unattended_execution",
        "setup_scripts",
        "cloud_init",
    ]
    return LambdaRemoteBootstrapScopeReport(
        bootstrap_scope_status="scoped_for_future_m051_review",
        default_experiment_type=default_experiment_type,
        allowed_future_experiment_types=[
            "lifecycle_plus_metadata_only",
            "lifecycle_plus_ssh_connectivity_check",
            "lifecycle_plus_single_benign_command",
        ],
        forbidden_actions=forbidden_actions,
        required_operator_approval_items=[
            "future supervised launch approval",
            "explicit SSH approval before any SSH connection",
            "explicit command approval before any remote command",
            "owned-instance termination and read-only verification",
        ],
        warnings=[
            "M050 defines future M051 scope only",
            "default bootstrap mode is metadata-only and performs no SSH",
        ],
    )


def load_lambda_remote_bootstrap_scope(
    path: str | Path,
) -> LambdaRemoteBootstrapScopeReport:
    return LambdaRemoteBootstrapScopeReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_remote_bootstrap_scope(
    path: str | Path,
    report: LambdaRemoteBootstrapScopeReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
