"""Policy for waiting on SSH banner readiness before uploads."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LambdaSSHBannerReadinessPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M073S"
    policy_status: str = "policy_defined"
    tcp_22_reachability_sufficient_for_upload: bool = False
    banner_readiness_required_before_upload: bool = True
    raw_tcp_banner_probe_allowed: bool = True
    expected_banner_prefix: str = "SSH-2.0-"
    authentication_required_for_banner_probe: bool = False
    remote_command_allowed: bool = False
    file_transfer_allowed_during_probe: bool = False
    port_forwarding_allowed: bool = False
    max_banner_wait_seconds: int = 120
    per_attempt_timeout_seconds: int = 5
    max_attempts: int = 24
    fallback_no_command_ssh_readiness_check_allowed: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_policy(self) -> LambdaSSHBannerReadinessPolicy:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("SSH banner readiness policy must remain future-only")
        if self.remote_command_allowed or self.file_transfer_allowed_during_probe:
            raise ValueError("banner probe cannot run commands or transfer files")
        if self.tcp_22_reachability_sufficient_for_upload:
            raise ValueError("TCP/22 alone is not sufficient upload readiness")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_ssh_banner_readiness_policy() -> LambdaSSHBannerReadinessPolicy:
    return LambdaSSHBannerReadinessPolicy(
        warnings=[
            "future upload paths must observe an SSH banner before scp",
            "the banner probe does not authenticate, upload, or execute commands",
        ]
    )


def load_lambda_ssh_banner_readiness_policy(
    path: str | Path,
) -> LambdaSSHBannerReadinessPolicy:
    return LambdaSSHBannerReadinessPolicy.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_ssh_banner_readiness_policy(
    path: str | Path,
    report: LambdaSSHBannerReadinessPolicy,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
