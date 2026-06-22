"""Future SSH retry policy for live-candidate selection."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.ssh_capacity_history import load_lambda_ssh_capacity_history
from decodilo.lambda_cloud.ssh_failure_stderr_capture import (
    load_lambda_ssh_stderr_capture_policy,
)

LambdaSSHRetryCandidatePolicyStatus = Literal["policy_passed", "blocked"]


class LambdaSSHRetryCandidatePolicyReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    policy_status: LambdaSSHRetryCandidatePolicyStatus
    no_automatic_retry: bool = True
    same_candidate_region_retry_requires_fresh_live_availability: bool = True
    unknown_exit_255_requires_redacted_stderr_capture: bool = True
    username_required: str = "ubuntu"
    identities_only_required: bool = True
    isolated_known_hosts_required: bool = True
    redacted_stderr_capture_required: bool = True
    max_ssh_attempts: int = 1
    no_remote_command: bool = True
    no_file_transfer: bool = True
    no_port_forwarding: bool = True
    no_package_install: bool = True
    no_training: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> LambdaSSHRetryCandidatePolicyReport:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or not self.no_automatic_retry
            or self.max_ssh_attempts != 1
        ):
            raise ValueError("SSH retry candidate policy cannot enable launch or retry")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_ssh_retry_candidate_policy_from_paths(
    *,
    capacity_history: str | Path,
    stderr_policy: str | Path,
) -> LambdaSSHRetryCandidatePolicyReport:
    history = load_lambda_ssh_capacity_history(capacity_history)
    stderr = load_lambda_ssh_stderr_capture_policy(stderr_policy)
    blockers: list[str] = []
    if stderr.capture_policy_status != "policy_defined" or not stderr.secret_scan_passed:
        blockers.extend(stderr.blockers or ["stderr_capture_policy_not_active"])
    if not history.capacity_rejections_count:
        blockers.append("capacity_history_has_no_capacity_rejection")
    return LambdaSSHRetryCandidatePolicyReport(
        policy_status="policy_passed" if not blockers else "blocked",
        blockers=sorted(set(blockers)),
        warnings=[
            "future retry is one-shot and operator-supervised only",
            "same candidate/region retry remains blocked without fresh live availability",
        ],
    )


def load_lambda_ssh_retry_candidate_policy(
    path: str | Path,
) -> LambdaSSHRetryCandidatePolicyReport:
    return LambdaSSHRetryCandidatePolicyReport.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_ssh_retry_candidate_policy(
    path: str | Path,
    report: LambdaSSHRetryCandidatePolicyReport,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
