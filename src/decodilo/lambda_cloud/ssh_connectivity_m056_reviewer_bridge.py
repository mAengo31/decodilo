"""Reviewer bridge for the M056 one-shot SSH retry."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.ssh_connectivity_m056_one_shot_arming import (
    is_lambda_ssh_connectivity_m056_one_shot_arming_expired,
    load_lambda_ssh_connectivity_m056_one_shot_arming,
)

LambdaSSHConnectivityM056ReviewerBridgeStatus = Literal[
    "not_ready",
    "reviewer_compatible_one_shot_ready",
]


class LambdaSSHConnectivityM056ReviewerBridge(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    bridge_status: LambdaSSHConnectivityM056ReviewerBridgeStatus
    one_shot_request_send_permitted: bool
    one_shot_ssh_connectivity_probe_permitted: bool
    selected_candidate: str | None = None
    selected_region: str | None = None
    max_launch_attempts: int = 1
    max_ssh_connectivity_attempts: int = 1
    no_auto_retry: bool = True
    no_remote_exec: bool = True
    no_file_transfer: bool = True
    no_port_forwarding: bool = True
    no_package_install: bool = True
    no_training: bool = True
    stderr_capture_enabled: bool = True
    owned_termination_required: bool = True
    termination_verification_required: bool = True
    standing_launch_ready: bool = False
    standing_launch_allowed: bool = False
    expires_at_utc: str | None = None
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_bridge(self) -> LambdaSSHConnectivityM056ReviewerBridge:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.standing_launch_ready
            or self.standing_launch_allowed
        ):
            raise ValueError("M056 reviewer bridge cannot enable standing launch")
        if (
            self.max_launch_attempts != 1
            or self.max_ssh_connectivity_attempts != 1
            or not self.no_auto_retry
            or not self.no_remote_exec
            or not self.no_file_transfer
            or not self.no_port_forwarding
            or not self.no_package_install
            or not self.no_training
            or not self.stderr_capture_enabled
            or not self.owned_termination_required
            or not self.termination_verification_required
        ):
            raise ValueError("M056 reviewer bridge violates one-shot constraints")
        if self.bridge_status == "reviewer_compatible_one_shot_ready":
            if self.blockers:
                raise ValueError("ready M056 bridge cannot have blockers")
            if not self.one_shot_request_send_permitted:
                raise ValueError("ready bridge requires request-send permission")
            if not self.one_shot_ssh_connectivity_probe_permitted:
                raise ValueError("ready bridge requires SSH probe permission")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_ssh_connectivity_m056_reviewer_bridge_from_path(
    *,
    arming: str | Path,
    now_utc: str | None = None,
) -> LambdaSSHConnectivityM056ReviewerBridge:
    arming_report = load_lambda_ssh_connectivity_m056_one_shot_arming(arming)
    blockers = list(arming_report.blockers)
    if arming_report.arming_status != "armed_for_one_shot_m056_ssh_retry":
        blockers.append("m056_one_shot_arming_not_armed")
    if is_lambda_ssh_connectivity_m056_one_shot_arming_expired(
        arming_report,
        now_utc=now_utc,
    ):
        blockers.append("m056_one_shot_arming_expired")
    status: LambdaSSHConnectivityM056ReviewerBridgeStatus = (
        "reviewer_compatible_one_shot_ready" if not blockers else "not_ready"
    )
    return LambdaSSHConnectivityM056ReviewerBridge(
        bridge_status=status,
        one_shot_request_send_permitted=status == "reviewer_compatible_one_shot_ready",
        one_shot_ssh_connectivity_probe_permitted=(
            status == "reviewer_compatible_one_shot_ready"
        ),
        selected_candidate=arming_report.selected_candidate,
        selected_region=arming_report.selected_region,
        expires_at_utc=arming_report.expires_at_utc,
        blockers=sorted(set(blockers)),
        warnings=[
            "reviewer bridge is the only M056 artifact exposing one-shot permissions",
            "standing launch_ready and launch_allowed remain false",
        ],
    )


def load_lambda_ssh_connectivity_m056_reviewer_bridge(
    path: str | Path,
) -> LambdaSSHConnectivityM056ReviewerBridge:
    return LambdaSSHConnectivityM056ReviewerBridge.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_ssh_connectivity_m056_reviewer_bridge(
    path: str | Path,
    report: LambdaSSHConnectivityM056ReviewerBridge,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
