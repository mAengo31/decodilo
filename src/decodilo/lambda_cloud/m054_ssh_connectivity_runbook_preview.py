"""Non-executable M054 SSH-connectivity runbook preview."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.m054_ssh_connectivity_authorization import (
    load_lambda_m054_ssh_connectivity_authorization,
)


class LambdaM054SSHConnectivityRunbookPreview(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    preview_status: str
    executable: bool = False
    authorization_status: str
    future_workdir_placeholder: str = "/tmp/decodilo-lambda-m054"
    lifecycle_requirements: list[str] = Field(default_factory=list)
    forbidden_actions: list[str] = Field(default_factory=list)
    max_budget: float = 50.0
    max_runtime_minutes: int = 30
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_preview(self) -> LambdaM054SSHConnectivityRunbookPreview:
        if (
            self.executable
            or self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M054 runbook preview must be non-executable")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m054_ssh_connectivity_runbook_preview_from_path(
    authorization: str | Path,
) -> LambdaM054SSHConnectivityRunbookPreview:
    auth = load_lambda_m054_ssh_connectivity_authorization(authorization)
    ready = auth.authorization_status == "authorized_for_future_m054_ssh_connectivity_review"
    return LambdaM054SSHConnectivityRunbookPreview(
        preview_status=(
            "ready_for_future_m054_ssh_connectivity_review" if ready else "blocked_not_authorized"
        ),
        authorization_status=auth.authorization_status,
        lifecycle_requirements=[
            "future supervised launch of at most one instance if separately armed",
            "collect provider-visible IP or hostname only",
            "bounded SSH handshake/authentication check only if M054 is approved",
            "terminate exactly the owned instance if created",
            "verify terminal or absent state through Lambda read-only discovery/list/get",
        ],
        forbidden_actions=[
            "interactive shell",
            "remote command",
            "file transfer",
            "port forwarding",
            "package install",
            "cloud-init",
            "setup script",
            "training",
        ],
        blockers=auth.blockers,
        warnings=[
            "M053 does not execute this preview",
            "runbook preview is non-executable",
            *auth.warnings,
        ],
    )


def load_lambda_m054_ssh_connectivity_runbook_preview(
    path: str | Path,
) -> LambdaM054SSHConnectivityRunbookPreview:
    return LambdaM054SSHConnectivityRunbookPreview.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_m054_ssh_connectivity_runbook_preview(
    path: str | Path,
    report: LambdaM054SSHConnectivityRunbookPreview,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
