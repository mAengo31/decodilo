"""Future-only M065 Python runtime version query authorization."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.gpu_visibility_closeout import (
    load_lambda_gpu_visibility_closeout,
)
from decodilo.lambda_cloud.python_runtime_command_policy import (
    M065_PYTHON_RUNTIME_COMMAND,
    load_lambda_python_runtime_command_policy,
)
from decodilo.lambda_cloud.python_runtime_command_review import (
    load_lambda_python_runtime_command_review,
)
from decodilo.lambda_cloud.python_runtime_output_policy import (
    load_lambda_python_runtime_output_policy,
)

LambdaM065PythonRuntimeAuthorizationStatus = Literal[
    "not_authorized",
    "authorized_for_future_m065_python_version_query_review",
]


class LambdaM065PythonRuntimeAuthorization(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    authorization_status: LambdaM065PythonRuntimeAuthorizationStatus
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
    def _validate_future_only(self) -> LambdaM065PythonRuntimeAuthorization:
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
            raise ValueError("M065 authorization cannot authorize immediate execution")
        if (
            self.authorization_status
            == "authorized_for_future_m065_python_version_query_review"
        ):
            if (
                self.blockers
                or self.selected_command != M065_PYTHON_RUNTIME_COMMAND
                or self.selected_future_command_set != [M065_PYTHON_RUNTIME_COMMAND]
            ):
                raise ValueError("M065 authorization requires exact future Python query")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m065_python_runtime_authorization_from_paths(
    *,
    gpu_visibility_closeout: str | Path,
    command_policy: str | Path,
    output_policy: str | Path,
    command_review: str | Path,
) -> LambdaM065PythonRuntimeAuthorization:
    closeout = load_lambda_gpu_visibility_closeout(gpu_visibility_closeout)
    command = load_lambda_python_runtime_command_policy(command_policy)
    output = load_lambda_python_runtime_output_policy(output_policy)
    review = load_lambda_python_runtime_command_review(command_review)
    blockers = [
        *closeout.blockers,
        *command.blockers,
        *output.blockers,
        *review.blockers,
    ]
    if not closeout.closeout_succeeded:
        blockers.append("gpu_visibility_closeout_not_succeeded")
    if closeout.closeout_status not in {"closed_success", "closed_with_warnings"}:
        blockers.append("gpu_visibility_closeout_not_closed")
    if command.policy_status != "python_runtime_command_policy_defined_future_only":
        blockers.append("python_runtime_command_policy_not_passed")
    if output.output_policy_status != "python_runtime_output_policy_defined_future_only":
        blockers.append("python_runtime_output_policy_not_passed")
    if review.command_review_status != "python_runtime_command_review_passed_future_only":
        blockers.append("python_runtime_command_review_not_passed")
    if review.selected_future_command_set != [M065_PYTHON_RUNTIME_COMMAND]:
        blockers.append("m065_future_command_not_exact_python_version_query")
    status: LambdaM065PythonRuntimeAuthorizationStatus = (
        "authorized_for_future_m065_python_version_query_review"
        if not blockers
        else "not_authorized"
    )
    return LambdaM065PythonRuntimeAuthorization(
        authorization_status=status,
        selected_future_command_set=(
            [M065_PYTHON_RUNTIME_COMMAND] if status != "not_authorized" else []
        ),
        selected_command=(M065_PYTHON_RUNTIME_COMMAND if status != "not_authorized" else None),
        blockers=sorted(set(blockers)),
        warnings=[
            "M065 authorization is future-only and does not permit execution now",
            (
                "Package installation, training, imports, scripts, shell wrappers, "
                "transfers, and port forwarding remain forbidden"
            ),
        ],
    )


def load_lambda_m065_python_runtime_authorization(
    path: str | Path,
) -> LambdaM065PythonRuntimeAuthorization:
    return LambdaM065PythonRuntimeAuthorization.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_m065_python_runtime_authorization(
    path: str | Path,
    report: LambdaM065PythonRuntimeAuthorization,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
