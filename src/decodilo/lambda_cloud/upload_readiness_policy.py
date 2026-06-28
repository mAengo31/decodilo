"""Upload readiness gate policy for future M073R2 retries."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.ssh_banner_readiness_policy import (
    load_lambda_ssh_banner_readiness_policy,
)


class LambdaUploadReadinessGatePolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    milestone: str = "M073S"
    gate_policy_status: str
    host_discovery_required: bool = True
    tcp_22_reachable_required: bool = True
    ssh_banner_readiness_required: bool = True
    optional_post_banner_stabilization_delay_allowed: bool = True
    max_readiness_wait_seconds: int = 180
    upload_before_readiness_allowed: bool = False
    upload_failure_retry_allowed: bool = False
    max_source_upload_attempts: int = 1
    max_dependency_upload_attempts: int = 1
    no_extra_file_transfers: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False

    @model_validator(mode="after")
    def _validate_gate_policy(self) -> LambdaUploadReadinessGatePolicy:
        if self.launch_ready or self.launch_allowed or self.billable_action_performed:
            raise ValueError("upload readiness policy must remain future-only")
        if self.upload_before_readiness_allowed or self.upload_failure_retry_allowed:
            raise ValueError("upload policy cannot allow pre-readiness upload or retry")
        if self.max_source_upload_attempts != 1 or self.max_dependency_upload_attempts != 1:
            raise ValueError("M073R2 upload attempts must be one-shot")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_upload_readiness_gate_policy_from_path(
    *,
    banner_policy: str | Path,
) -> LambdaUploadReadinessGatePolicy:
    banner = load_lambda_ssh_banner_readiness_policy(banner_policy)
    blockers: list[str] = []
    if not banner.banner_readiness_required_before_upload:
        blockers.append("banner_readiness_not_required")
    if banner.tcp_22_reachability_sufficient_for_upload:
        blockers.append("tcp_22_marked_sufficient")
    return LambdaUploadReadinessGatePolicy(
        gate_policy_status="policy_defined" if not blockers else "blocked",
        blockers=blockers,
        warnings=["M073R2 must not attempt scp until banner readiness is observed"],
    )


def load_lambda_upload_readiness_gate_policy(
    path: str | Path,
) -> LambdaUploadReadinessGatePolicy:
    return LambdaUploadReadinessGatePolicy.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_upload_readiness_gate_policy(
    path: str | Path,
    report: LambdaUploadReadinessGatePolicy,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
