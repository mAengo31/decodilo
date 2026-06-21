"""Reviewer-compatible one-shot bridge for M051 metadata bootstrap."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.m051_artifact_binding import (
    load_lambda_m051_artifact_binding,
)
from decodilo.lambda_cloud.m051_exact_command_binding import (
    load_lambda_m051_exact_command_binding,
)
from decodilo.lambda_cloud.m051_one_shot_arming import (
    is_m051_one_shot_arming_expired,
    load_lambda_m051_one_shot_arming,
)

LambdaM051ExecutionReviewerBridgeStatus = Literal[
    "not_ready",
    "reviewer_compatible_one_shot_ready",
]


class LambdaM051ExecutionReviewerBridge(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    bridge_status: LambdaM051ExecutionReviewerBridgeStatus
    standing_artifacts_launch_allowed: bool = False
    standing_artifacts_launch_ready: bool = False
    standing_artifacts_launch_authorized_now: bool = False
    one_shot_request_send_permitted: bool
    selected_candidate: str | None = None
    selected_region: str | None = None
    command_hash: str | None = None
    artifact_binding_hash: str | None = None
    expires_at_utc: str | None = None
    max_launch_attempts: int = 1
    no_auto_retry: bool = True
    no_ssh: bool = True
    no_remote_commands: bool = True
    no_package_install: bool = True
    no_training: bool = True
    owned_termination_required: bool = True
    termination_verification_required: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_bridge(self) -> LambdaM051ExecutionReviewerBridge:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.standing_artifacts_launch_ready
            or self.standing_artifacts_launch_allowed
            or self.standing_artifacts_launch_authorized_now
        ):
            raise ValueError("M051 reviewer bridge cannot enable standing launch")
        if (
            self.max_launch_attempts != 1
            or not self.no_auto_retry
            or not self.no_ssh
            or not self.no_remote_commands
            or not self.no_package_install
            or not self.no_training
            or not self.owned_termination_required
            or not self.termination_verification_required
        ):
            raise ValueError("M051 reviewer bridge violates one-shot constraints")
        if self.bridge_status == "reviewer_compatible_one_shot_ready":
            if self.blockers:
                raise ValueError("ready M051 reviewer bridge cannot have blockers")
            if not self.one_shot_request_send_permitted:
                raise ValueError("ready M051 reviewer bridge requires one-shot permission")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m051_execution_reviewer_bridge_from_paths(
    *,
    arming: str | Path,
    command_binding: str | Path,
    artifact_binding: str | Path,
    now_utc: str | None = None,
) -> LambdaM051ExecutionReviewerBridge:
    arming_report = load_lambda_m051_one_shot_arming(arming)
    command_report = load_lambda_m051_exact_command_binding(command_binding)
    artifact_report = load_lambda_m051_artifact_binding(artifact_binding)
    blockers: list[str] = []
    if arming_report.arming_status != "armed_for_one_shot_m051_metadata_bootstrap":
        blockers.extend(arming_report.blockers or ["m051_one_shot_arming_not_armed"])
    if is_m051_one_shot_arming_expired(arming_report, now_utc=now_utc):
        blockers.append("m051_one_shot_arming_expired")
    if not command_report.binding_passed:
        blockers.extend(command_report.blockers or ["m051_command_binding_failed"])
    if not artifact_report.binding_passed:
        blockers.extend(artifact_report.blockers or ["m051_artifact_binding_failed"])
    if (
        arming_report.standing_launch_allowed
        or arming_report.standing_launch_ready
        or arming_report.standing_launch_authorized_now
    ):
        blockers.append("standing_launch_flag_enabled")
    if arming_report.max_launch_attempts != 1:
        blockers.append("max_launch_attempts_not_one")
    if not arming_report.no_auto_retry:
        blockers.append("automatic_retry_enabled")
    status: LambdaM051ExecutionReviewerBridgeStatus = (
        "reviewer_compatible_one_shot_ready" if not blockers else "not_ready"
    )
    return LambdaM051ExecutionReviewerBridge(
        bridge_status=status,
        one_shot_request_send_permitted=status == "reviewer_compatible_one_shot_ready",
        selected_candidate=arming_report.selected_candidate,
        selected_region=arming_report.selected_region,
        command_hash=command_report.command_hash,
        artifact_binding_hash=_sha256_file(artifact_binding),
        expires_at_utc=arming_report.expires_at_utc,
        max_launch_attempts=arming_report.max_launch_attempts,
        no_auto_retry=arming_report.no_auto_retry,
        no_ssh=arming_report.no_ssh,
        no_remote_commands=arming_report.no_remote_commands,
        no_package_install=arming_report.no_package_install,
        no_training=arming_report.no_training,
        owned_termination_required=arming_report.terminate_owned_instance_required,
        termination_verification_required=arming_report.termination_verification_required,
        blockers=sorted(set(blockers)),
        warnings=[
            "reviewer bridge is the only artifact that may expose one-shot permission",
            "standing launch_ready and launch_allowed remain false",
        ],
    )


def _sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_lambda_m051_execution_reviewer_bridge(
    path: str | Path,
) -> LambdaM051ExecutionReviewerBridge:
    return LambdaM051ExecutionReviewerBridge.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_m051_execution_reviewer_bridge(
    path: str | Path,
    report: LambdaM051ExecutionReviewerBridge,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
