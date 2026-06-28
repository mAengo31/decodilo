"""Review the smallest useful next remote command after M057."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.remote_command_stage_policy import (
    load_lambda_remote_command_stage_policy,
)

SmallestUsefulCommandStage = Literal[
    "identity_command",
    "gpu_visibility_command",
    "needs_more_evidence",
]


class LambdaSmallestUsefulCommandReview(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    review_status: Literal["review_passed", "blocked"]
    recommended_next_command_stage: SmallestUsefulCommandStage
    candidate_commands: list[str] = Field(default_factory=list)
    selected_future_command_set: list[str] = Field(default_factory=list)
    command_risk: str
    nvidia_smi_authorized: bool = False
    package_install_allowed: bool = False
    training_allowed: bool = False
    file_transfer_allowed: bool = False
    port_forwarding_allowed: bool = False
    immediate_execution_authorized: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_future_only(self) -> LambdaSmallestUsefulCommandReview:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.nvidia_smi_authorized
            or self.package_install_allowed
            or self.training_allowed
            or self.file_transfer_allowed
            or self.port_forwarding_allowed
            or self.immediate_execution_authorized
        ):
            raise ValueError("smallest command review cannot authorize immediate work")
        if self.selected_future_command_set and self.selected_future_command_set not in (
            ["hostname"],
            ["hostname", "whoami"],
        ):
            raise ValueError("M059 review can select only identity commands")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_smallest_useful_command_review_from_path(
    *,
    stage_policy: str | Path,
) -> LambdaSmallestUsefulCommandReview:
    policy = load_lambda_remote_command_stage_policy(stage_policy)
    blockers = list(policy.blockers)
    if policy.policy_status != "policy_defined":
        blockers.append("stage_policy_not_defined")
    if policy.current_accepted_stage != "noop_command_only":
        blockers.append("noop_stage_not_established")
    selected = [] if blockers else ["hostname"]
    return LambdaSmallestUsefulCommandReview(
        review_status="review_passed" if not blockers else "blocked",
        recommended_next_command_stage=(
            "identity_command" if not blockers else "needs_more_evidence"
        ),
        candidate_commands=["hostname", "whoami", "nvidia-smi", "python --version"],
        selected_future_command_set=selected,
        command_risk=(
            "low_identity_metadata_no_output_sensitive_by_design"
            if not blockers
            else "blocked"
        ),
        blockers=sorted(set(blockers)),
        warnings=[
            "M059 is future-only and should use hostname before GPU visibility commands",
            "nvidia-smi, python, package install, and training remain unauthorized",
        ],
    )


def load_lambda_smallest_useful_command_review(
    path: str | Path,
) -> LambdaSmallestUsefulCommandReview:
    return LambdaSmallestUsefulCommandReview.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_smallest_useful_command_review(
    path: str | Path,
    report: LambdaSmallestUsefulCommandReview,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
