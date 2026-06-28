"""Future-only M063 GPU visibility query authorization."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.gpu_visibility_command_policy import (
    M063_GPU_VISIBILITY_COMMAND,
    load_lambda_gpu_visibility_command_policy,
)
from decodilo.lambda_cloud.gpu_visibility_command_review import (
    load_lambda_gpu_visibility_command_review,
)
from decodilo.lambda_cloud.gpu_visibility_output_policy import (
    load_lambda_gpu_visibility_output_policy,
)
from decodilo.lambda_cloud.whoami_command_closeout import (
    load_lambda_whoami_command_closeout,
)

LambdaM063GPUVisibilityAuthorizationStatus = Literal[
    "not_authorized",
    "authorized_for_future_m063_gpu_visibility_query_review",
]


class LambdaM063GPUVisibilityAuthorization(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    authorization_status: LambdaM063GPUVisibilityAuthorizationStatus
    selected_future_command_set: list[str] = Field(default_factory=list)
    selected_command: str | None = None
    future_review_only: bool = True
    launch_authorized_now: bool = False
    command_authorized_now: bool = False
    package_install_allowed: bool = False
    training_allowed: bool = False
    file_transfer_allowed: bool = False
    port_forwarding_allowed: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_future_only(self) -> LambdaM063GPUVisibilityAuthorization:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.launch_authorized_now
            or self.command_authorized_now
            or self.package_install_allowed
            or self.training_allowed
            or self.file_transfer_allowed
            or self.port_forwarding_allowed
            or not self.future_review_only
        ):
            raise ValueError("M063 authorization cannot authorize immediate execution")
        if (
            self.authorization_status
            == "authorized_for_future_m063_gpu_visibility_query_review"
        ):
            if (
                self.blockers
                or self.selected_command != M063_GPU_VISIBILITY_COMMAND
                or self.selected_future_command_set != [M063_GPU_VISIBILITY_COMMAND]
            ):
                raise ValueError("M063 authorization requires exact future GPU query")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m063_gpu_visibility_authorization_from_paths(
    *,
    whoami_closeout: str | Path,
    command_policy: str | Path,
    output_policy: str | Path,
    command_review: str | Path,
) -> LambdaM063GPUVisibilityAuthorization:
    closeout = load_lambda_whoami_command_closeout(whoami_closeout)
    command = load_lambda_gpu_visibility_command_policy(command_policy)
    output = load_lambda_gpu_visibility_output_policy(output_policy)
    review = load_lambda_gpu_visibility_command_review(command_review)
    blockers = [
        *closeout.blockers,
        *command.blockers,
        *output.blockers,
        *review.blockers,
    ]
    if not closeout.closeout_succeeded:
        blockers.append("whoami_closeout_not_succeeded")
    if closeout.command != "whoami":
        blockers.append("whoami_closeout_command_not_whoami")
    if (
        command.command_policy_status
        != "gpu_visibility_command_policy_defined_future_only"
    ):
        blockers.append("gpu_visibility_command_policy_not_passed")
    if output.output_policy_status != "gpu_visibility_output_policy_defined_future_only":
        blockers.append("gpu_visibility_output_policy_not_passed")
    if review.command_review_status != "gpu_visibility_command_review_passed_future_only":
        blockers.append("gpu_visibility_command_review_not_passed")
    if review.selected_future_command_set != [M063_GPU_VISIBILITY_COMMAND]:
        blockers.append("m063_future_command_not_exact_gpu_query")
    status: LambdaM063GPUVisibilityAuthorizationStatus = (
        "authorized_for_future_m063_gpu_visibility_query_review"
        if not blockers
        else "not_authorized"
    )
    return LambdaM063GPUVisibilityAuthorization(
        authorization_status=status,
        selected_future_command_set=(
            [M063_GPU_VISIBILITY_COMMAND] if status != "not_authorized" else []
        ),
        selected_command=(M063_GPU_VISIBILITY_COMMAND if status != "not_authorized" else None),
        blockers=sorted(set(blockers)),
        warnings=[
            "M063 authorization is future-only and does not permit execution now",
            (
                "Package installation, training, file transfer, port forwarding, "
                "shell wrappers, and benchmarks remain forbidden"
            ),
        ],
    )


def load_lambda_m063_gpu_visibility_authorization(
    path: str | Path,
) -> LambdaM063GPUVisibilityAuthorization:
    return LambdaM063GPUVisibilityAuthorization.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_m063_gpu_visibility_authorization(
    path: str | Path,
    report: LambdaM063GPUVisibilityAuthorization,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
