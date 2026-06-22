"""One-shot arming artifact for the M056 SSH retry."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.ssh_connectivity_m056_gate_check import (
    load_lambda_ssh_connectivity_m056_gate_check,
)
from decodilo.lambda_cloud.ssh_connectivity_m056_plan import (
    M056_SELECTED_CANDIDATE,
    M056_SELECTED_REGION,
    load_lambda_ssh_connectivity_m056_plan,
)
from decodilo.lambda_cloud.ssh_retry_future_authorization import (
    load_lambda_ssh_retry_future_authorization,
)
from decodilo.lambda_cloud.strand_response_loss_control_check import (
    load_lambda_strand_response_loss_control_check,
)

ARMED_FOR_M056_SSH_RETRY = "m056_live_candidate_ssh_retry_single_launch_attempt"
LambdaSSHConnectivityM056OneShotArmingStatus = Literal[
    "not_armed",
    "armed_for_one_shot_m056_ssh_retry",
]


class LambdaSSHConnectivityM056OneShotArming(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    arming_id: str
    arming_status: LambdaSSHConnectivityM056OneShotArmingStatus
    armed_for: str = ARMED_FOR_M056_SSH_RETRY
    one_shot_request_send_permitted: bool = False
    request_send_permission_delegated_to_reviewer_bridge: bool = True
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
    terminate_owned_instance_required: bool = True
    termination_verification_required: bool = True
    created_at_utc: str
    expires_at_utc: str
    artifact_hashes: dict[str, str] = Field(default_factory=dict)
    artifact_paths: dict[str, str] = Field(default_factory=dict)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_arming(self) -> LambdaSSHConnectivityM056OneShotArming:
        if self.armed_for != ARMED_FOR_M056_SSH_RETRY:
            raise ValueError("M056 SSH retry arming target is invalid")
        if (
            self.one_shot_request_send_permitted
            or self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M056 arming cannot directly permit request send")
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
            or not self.terminate_owned_instance_required
            or not self.termination_verification_required
        ):
            raise ValueError("M056 arming violates one-shot SSH constraints")
        if self.arming_status == "armed_for_one_shot_m056_ssh_retry" and self.blockers:
            raise ValueError("armed M056 SSH arming artifact cannot have blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_ssh_connectivity_m056_one_shot_arming_from_paths(
    *,
    plan: str | Path,
    gate_check: str | Path,
    authorization: str | Path,
    response_loss_controls: str | Path,
    expires_minutes: int,
    created_at_utc: str | None = None,
) -> LambdaSSHConnectivityM056OneShotArming:
    paths = {
        "plan": str(plan),
        "gate_check": str(gate_check),
        "authorization": str(authorization),
        "response_loss_controls": str(response_loss_controls),
    }
    hashes = {name: _sha256_file(path) for name, path in paths.items() if Path(path).exists()}
    plan_report = load_lambda_ssh_connectivity_m056_plan(plan)
    gate = load_lambda_ssh_connectivity_m056_gate_check(gate_check)
    auth = load_lambda_ssh_retry_future_authorization(authorization)
    controls = load_lambda_strand_response_loss_control_check(response_loss_controls)
    blockers: list[str] = [*plan_report.blockers, *gate.blockers, *auth.blockers]
    if plan_report.plan_status != "plan_passed":
        blockers.append("m056_plan_not_passed")
    if not gate.gate_passed:
        blockers.append("m056_gate_not_passed")
    if (
        auth.authorization_status
        != "authorized_for_future_m056_live_candidate_ssh_retry_review"
    ):
        blockers.append("m056_authorization_not_ready")
    if not controls.controls_passed or not controls.no_auto_launch_retry:
        blockers.extend(controls.blockers or ["response_loss_controls_not_passed"])
    if plan_report.selected_candidate != M056_SELECTED_CANDIDATE:
        blockers.append("m056_plan_candidate_mismatch")
    if plan_report.selected_region != M056_SELECTED_REGION:
        blockers.append("m056_plan_region_mismatch")
    if gate.selected_candidate != plan_report.selected_candidate:
        blockers.append("m056_gate_candidate_mismatch")
    if gate.selected_region != plan_report.selected_region:
        blockers.append("m056_gate_region_mismatch")
    if expires_minutes <= 0:
        blockers.append("expiration_required")
    created = _parse_utc(created_at_utc) if created_at_utc else datetime.now(timezone.utc)
    expires = created + timedelta(minutes=expires_minutes)
    status: LambdaSSHConnectivityM056OneShotArmingStatus = (
        "armed_for_one_shot_m056_ssh_retry" if not blockers else "not_armed"
    )
    arming_id = "m056-ssh-one-shot-" + _hash_json(
        {
            "created_at_utc": _format_utc(created),
            "expires_at_utc": _format_utc(expires),
            "artifact_hashes": hashes,
            "selected_candidate": plan_report.selected_candidate,
            "selected_region": plan_report.selected_region,
        }
    )[:16]
    return LambdaSSHConnectivityM056OneShotArming(
        arming_id=arming_id,
        arming_status=status,
        selected_candidate=plan_report.selected_candidate,
        selected_region=plan_report.selected_region,
        created_at_utc=_format_utc(created),
        expires_at_utc=_format_utc(expires),
        artifact_hashes=hashes,
        artifact_paths=paths,
        blockers=sorted(set(blockers)),
        warnings=[
            "M056 arming is preview-only; reviewer bridge exposes one-shot permission",
            "standing launch_ready and launch_allowed remain false",
        ],
    )


def is_lambda_ssh_connectivity_m056_one_shot_arming_expired(
    report: LambdaSSHConnectivityM056OneShotArming,
    *,
    now_utc: str | None = None,
) -> bool:
    now = _parse_utc(now_utc) if now_utc else datetime.now(timezone.utc)
    return now >= _parse_utc(report.expires_at_utc)


def _sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _hash_json(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.astimezone(timezone.utc)


def load_lambda_ssh_connectivity_m056_one_shot_arming(
    path: str | Path,
) -> LambdaSSHConnectivityM056OneShotArming:
    return LambdaSSHConnectivityM056OneShotArming.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_ssh_connectivity_m056_one_shot_arming(
    path: str | Path,
    report: LambdaSSHConnectivityM056OneShotArming,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
