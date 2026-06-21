"""Future-only SSH-connectivity scope for Lambda bootstrap planning."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

LambdaSSHConnectivityScopeStatus = Literal["scope_defined", "blocked"]

ALLOWED_FUTURE_MODES = (
    "ssh_connectivity_handshake_only",
    "ssh_auth_check_only",
)

FORBIDDEN_ACTIONS = (
    "interactive_shell",
    "remote_exec",
    "file_transfer",
    "port_forwarding",
    "package_install",
    "setup_script",
    "cloud_init",
    "training",
    "background_process",
    "unattended_execution",
)


class LambdaSSHConnectivityScopeReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    scope_status: LambdaSSHConnectivityScopeStatus = "scope_defined"
    future_milestone: str = "M054"
    max_instances: int = 1
    max_runtime_minutes: int = 30
    max_budget: float = 50.0
    allowed_future_modes: list[str] = Field(default_factory=lambda: list(ALLOWED_FUTURE_MODES))
    forbidden_actions: list[str] = Field(default_factory=lambda: list(FORBIDDEN_ACTIONS))
    owned_termination_required: bool = True
    termination_verification_required: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_scope(self) -> LambdaSSHConnectivityScopeReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M053 SSH connectivity scope cannot enable execution")
        if self.max_instances != 1:
            raise ValueError("SSH connectivity scope is limited to one instance")
        missing_forbidden = set(FORBIDDEN_ACTIONS).difference(self.forbidden_actions)
        if missing_forbidden:
            raise ValueError(
                f"missing forbidden SSH connectivity actions: {sorted(missing_forbidden)}"
            )
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


LambdaSSHConnectivityScope = LambdaSSHConnectivityScopeReport


def build_lambda_ssh_connectivity_scope() -> LambdaSSHConnectivityScopeReport:
    return LambdaSSHConnectivityScopeReport(
        warnings=[
            "M053 defines future SSH-connectivity review scope only",
            (
                "SSH connectivity-only excludes shells, commands, file transfer, "
                "forwarding, installs, and training"
            ),
        ],
    )


def load_lambda_ssh_connectivity_scope(path: str | Path) -> LambdaSSHConnectivityScopeReport:
    return LambdaSSHConnectivityScopeReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_ssh_connectivity_scope(
    path: str | Path,
    report: LambdaSSHConnectivityScopeReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
