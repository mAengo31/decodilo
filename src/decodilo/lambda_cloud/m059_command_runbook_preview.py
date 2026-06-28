"""Non-executable runbook preview for future M059 identity command review."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.m059_remote_command_authorization import (
    load_lambda_m059_remote_command_authorization,
)


class LambdaM059CommandRunbookPreview(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    preview_status: str
    executable: bool = False
    selected_future_command_set: list[str] = Field(default_factory=list)
    max_instances: int = 1
    max_budget: float = 50.0
    max_runtime_minutes: int = 30
    ssh_required: bool = True
    terminate_owned_instance_required: bool = True
    termination_verification_required: bool = True
    package_install_allowed: bool = False
    training_allowed: bool = False
    file_transfer_allowed: bool = False
    port_forwarding_allowed: bool = False
    runbook_steps: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_non_executable(self) -> LambdaM059CommandRunbookPreview:
        if (
            self.executable
            or self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.package_install_allowed
            or self.training_allowed
            or self.file_transfer_allowed
            or self.port_forwarding_allowed
        ):
            raise ValueError("M059 runbook preview must remain non-executable")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m059_command_runbook_preview_from_path(
    *,
    authorization: str | Path,
) -> LambdaM059CommandRunbookPreview:
    auth = load_lambda_m059_remote_command_authorization(authorization)
    ready = (
        auth.authorization_status
        == "authorized_for_future_m059_identity_command_review"
    )
    return LambdaM059CommandRunbookPreview(
        preview_status=(
            "ready_for_future_m059_identity_command_review" if ready else "blocked"
        ),
        selected_future_command_set=auth.selected_future_command_set,
        runbook_steps=[
            "Run fresh read-only discovery before any future launch.",
            "Launch at most one selected instance in supervised mode.",
            "Wait for provider host metadata and TCP/22 readiness.",
            "Run only the authorized identity command set.",
            "Store bounded redacted diagnostics only.",
            "Terminate the owned instance and verify termination through Lambda read-only APIs.",
        ],
        blockers=list(auth.blockers),
        warnings=[
            "This is a preview only; M058 does not execute this runbook",
            "M059 still requires explicit operator approval and one-shot arming",
        ],
    )


def load_lambda_m059_command_runbook_preview(
    path: str | Path,
) -> LambdaM059CommandRunbookPreview:
    return LambdaM059CommandRunbookPreview.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_m059_command_runbook_preview(
    path: str | Path,
    report: LambdaM059CommandRunbookPreview,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
