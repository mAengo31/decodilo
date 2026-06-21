"""One-shot arming artifact for future M054B SSH connectivity review."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.m054_ssh_connectivity_authorization import (
    load_lambda_m054_ssh_connectivity_authorization,
)
from decodilo.lambda_cloud.ssh_connectivity_execution_plan import (
    load_lambda_ssh_connectivity_execution_plan,
)
from decodilo.lambda_cloud.ssh_connectivity_static_validator import (
    load_lambda_ssh_connectivity_static_validation,
)

ARMED_FOR_M054_SSH_CONNECTIVITY = "m054_ssh_connectivity_only_single_launch_attempt"
LambdaSSHConnectivityOneShotArmingStatus = Literal[
    "not_armed",
    "armed_for_one_shot_m054_ssh_connectivity",
]


class LambdaSSHConnectivityOneShotArming(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    arming_id: str
    arming_status: LambdaSSHConnectivityOneShotArmingStatus
    armed_for: str = ARMED_FOR_M054_SSH_CONNECTIVITY
    one_shot_request_send_permitted: bool = False
    request_send_permission_delegated_to_reviewer_bridge: bool = True
    max_launch_attempts: int = 1
    max_ssh_connectivity_attempts: int = 1
    no_auto_retry: bool = True
    no_remote_exec: bool = True
    no_file_transfer: bool = True
    no_port_forwarding: bool = True
    no_package_install: bool = True
    no_training: bool = True
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
    def _validate_arming(self) -> LambdaSSHConnectivityOneShotArming:
        if self.armed_for != ARMED_FOR_M054_SSH_CONNECTIVITY:
            raise ValueError("M054 SSH arming target is invalid")
        if (
            self.one_shot_request_send_permitted
            or self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M054 arming cannot directly permit request send")
        if (
            self.max_launch_attempts != 1
            or self.max_ssh_connectivity_attempts != 1
            or not self.no_auto_retry
            or not self.no_remote_exec
            or not self.no_file_transfer
            or not self.no_port_forwarding
            or not self.no_package_install
            or not self.no_training
            or not self.terminate_owned_instance_required
            or not self.termination_verification_required
        ):
            raise ValueError("M054 arming violates one-shot SSH constraints")
        if self.arming_status == "armed_for_one_shot_m054_ssh_connectivity" and self.blockers:
            raise ValueError("armed M054 SSH arming artifact cannot have blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_ssh_connectivity_one_shot_arming_from_paths(
    *,
    execution_plan: str | Path,
    static_validation: str | Path,
    authorization: str | Path,
    expires_minutes: int,
    created_at_utc: str | None = None,
) -> LambdaSSHConnectivityOneShotArming:
    paths = {
        "execution_plan": str(execution_plan),
        "static_validation": str(static_validation),
        "authorization": str(authorization),
    }
    hashes = {name: _sha256_file(path) for name, path in paths.items() if Path(path).exists()}
    plan = load_lambda_ssh_connectivity_execution_plan(execution_plan)
    static = load_lambda_ssh_connectivity_static_validation(static_validation)
    auth = load_lambda_m054_ssh_connectivity_authorization(authorization)
    blockers = [*plan.blockers, *static.blockers, *auth.blockers]
    if plan.plan_status != "plan_defined":
        blockers.append("execution_plan_not_defined")
    if not static.static_validation_passed:
        blockers.append("static_validation_not_passed")
    if auth.authorization_status != "authorized_for_future_m054_ssh_connectivity_review":
        blockers.append("m054_authorization_not_ready")
    if expires_minutes <= 0:
        blockers.append("expiration_required")
    created = _parse_utc(created_at_utc) if created_at_utc else datetime.now(timezone.utc)
    expires = created + timedelta(minutes=expires_minutes)
    status: LambdaSSHConnectivityOneShotArmingStatus = (
        "armed_for_one_shot_m054_ssh_connectivity" if not blockers else "not_armed"
    )
    arming_id = "m054-ssh-one-shot-" + _hash_json(
        {
            "created_at_utc": _format_utc(created),
            "expires_at_utc": _format_utc(expires),
            "artifact_hashes": hashes,
        }
    )[:16]
    return LambdaSSHConnectivityOneShotArming(
        arming_id=arming_id,
        arming_status=status,
        created_at_utc=_format_utc(created),
        expires_at_utc=_format_utc(expires),
        artifact_hashes=hashes,
        artifact_paths=paths,
        blockers=sorted(set(blockers)),
        warnings=[
            "M054A arming is preview-only; reviewer bridge may expose one-shot permission",
            "standing launch_ready and launch_allowed remain false",
        ],
    )


def is_lambda_ssh_connectivity_one_shot_arming_expired(
    report: LambdaSSHConnectivityOneShotArming,
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


def load_lambda_ssh_connectivity_one_shot_arming(
    path: str | Path,
) -> LambdaSSHConnectivityOneShotArming:
    return LambdaSSHConnectivityOneShotArming.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_ssh_connectivity_one_shot_arming(
    path: str | Path,
    report: LambdaSSHConnectivityOneShotArming,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
