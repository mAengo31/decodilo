"""Ephemeral one-shot arming artifact for M051 metadata bootstrap."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.m051_bootstrap_authorization import (
    load_lambda_m051_bootstrap_authorization,
)
from decodilo.lambda_cloud.m051_bootstrap_execution_gate import (
    load_lambda_m051_bootstrap_execution_gate,
)
from decodilo.lambda_cloud.m051_metadata_bootstrap_plan import (
    load_lambda_m051_metadata_bootstrap_plan,
)
from decodilo.lambda_cloud.m051_no_mutation_no_ssh_audit import (
    load_lambda_m051_no_mutation_no_ssh_audit,
)
from decodilo.lambda_cloud.m051_operator_confirmation import (
    load_lambda_m051_operator_confirmation,
)
from decodilo.lambda_cloud.strand_response_loss_control_check import (
    load_lambda_strand_response_loss_control_check,
)

LambdaM051OneShotArmingStatus = Literal[
    "not_armed",
    "armed_for_one_shot_m051_metadata_bootstrap",
]

ARMED_FOR_M051_METADATA_ONLY = "m051_metadata_only_single_launch_attempt"
DEFAULT_M051_WORKDIR = "/tmp/decodilo-lambda-m051"


class LambdaM051OneShotArming(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    arming_id: str
    arming_status: LambdaM051OneShotArmingStatus
    armed_for: str = ARMED_FOR_M051_METADATA_ONLY
    one_shot_request_send_permitted: bool = False
    request_send_permission_delegated_to_reviewer_bridge: bool = True
    max_launch_attempts: int = 1
    max_mutating_operations: int = 2
    no_auto_retry: bool = True
    expires_at_utc: str
    created_at_utc: str
    workdir: str = DEFAULT_M051_WORKDIR
    selected_candidate: str | None = None
    selected_region: str | None = None
    no_ssh: bool = True
    no_remote_commands: bool = True
    no_package_install: bool = True
    no_training: bool = True
    terminate_owned_instance_required: bool = True
    termination_verification_required: bool = True
    operator_confirmation_hash: str | None = None
    metadata_plan_hash: str | None = None
    execution_gate_hash: str | None = None
    no_mutation_no_ssh_audit_hash: str | None = None
    bootstrap_authorization_hash: str | None = None
    response_loss_controls_hash: str | None = None
    exact_command_hash: str | None = None
    artifact_hashes: dict[str, str] = Field(default_factory=dict)
    artifact_paths: dict[str, str] = Field(default_factory=dict)
    standing_launch_ready: bool = False
    standing_launch_allowed: bool = False
    standing_launch_authorized_now: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_one_shot(self) -> LambdaM051OneShotArming:
        if self.armed_for != ARMED_FOR_M051_METADATA_ONLY:
            raise ValueError("M051 one-shot arming has an invalid target")
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.standing_launch_ready
            or self.standing_launch_allowed
            or self.standing_launch_authorized_now
        ):
            raise ValueError("M051 one-shot arming cannot enable standing launch")
        if self.one_shot_request_send_permitted:
            raise ValueError(
                "one_shot_request_send_permitted may be true only in reviewer bridge"
            )
        if (
            self.max_launch_attempts != 1
            or self.max_mutating_operations != 2
            or not self.no_auto_retry
            or not self.no_ssh
            or not self.no_remote_commands
            or not self.no_package_install
            or not self.no_training
        ):
            raise ValueError("M051 one-shot arming violates execution constraints")
        if self.arming_status == "armed_for_one_shot_m051_metadata_bootstrap":
            if self.blockers:
                raise ValueError("armed M051 one-shot artifact cannot have blockers")
            if not self.expires_at_utc or not self.operator_confirmation_hash:
                raise ValueError("armed M051 one-shot artifact requires bound hashes")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m051_one_shot_arming_from_paths(
    *,
    operator_confirmation: str | Path,
    metadata_plan: str | Path,
    execution_gate: str | Path,
    no_mutation_no_ssh_audit: str | Path,
    bootstrap_authorization: str | Path,
    response_loss_controls: str | Path,
    expires_minutes: int,
    workdir: str = DEFAULT_M051_WORKDIR,
    created_at_utc: str | None = None,
) -> LambdaM051OneShotArming:
    artifact_paths = {
        "operator_confirmation": str(operator_confirmation),
        "metadata_plan": str(metadata_plan),
        "execution_gate": str(execution_gate),
        "no_mutation_no_ssh_audit": str(no_mutation_no_ssh_audit),
        "bootstrap_authorization": str(bootstrap_authorization),
        "response_loss_controls": str(response_loss_controls),
    }
    artifact_hashes = {
        name: _sha256_file(path)
        for name, path in artifact_paths.items()
        if Path(path).exists()
    }
    confirmation = load_lambda_m051_operator_confirmation(operator_confirmation)
    plan = load_lambda_m051_metadata_bootstrap_plan(metadata_plan)
    gate = load_lambda_m051_bootstrap_execution_gate(execution_gate)
    audit = load_lambda_m051_no_mutation_no_ssh_audit(no_mutation_no_ssh_audit)
    authorization = load_lambda_m051_bootstrap_authorization(bootstrap_authorization)
    controls = load_lambda_strand_response_loss_control_check(response_loss_controls)

    created = parse_utc(created_at_utc) if created_at_utc else datetime.now(timezone.utc)
    expires = created + timedelta(minutes=expires_minutes)
    blockers: list[str] = []
    if confirmation.confirmation_status != "confirmed_for_m051_one_shot_metadata_bootstrap":
        blockers.extend(confirmation.blockers or ["operator_confirmation_missing"])
    if not plan.plan_passed:
        blockers.extend(plan.blockers or ["metadata_plan_not_passed"])
    if not gate.gate_passed:
        blockers.extend(gate.blockers or ["execution_gate_not_passed"])
    if not audit.audit_passed:
        blockers.extend(audit.blockers or ["no_mutation_no_ssh_audit_failed"])
    if authorization.authorization_status != (
        "authorized_for_future_m051_metadata_only_bootstrap_review"
    ):
        blockers.extend(authorization.blockers or ["m051_authorization_not_ready"])
    if not controls.controls_passed or not controls.no_auto_launch_retry:
        blockers.extend(controls.blockers or ["response_loss_controls_not_passed"])
    if expires_minutes <= 0:
        blockers.append("expiration_required")
    if plan.ssh_used or gate.ssh_used:
        blockers.append("ssh_used_flag_true")
    if plan.remote_commands_allowed or gate.remote_commands_allowed:
        blockers.append("remote_commands_allowed_flag_true")
    if plan.package_install_allowed or gate.package_install_allowed:
        blockers.append("package_install_allowed_flag_true")
    if plan.training_allowed or gate.training_allowed:
        blockers.append("training_allowed_flag_true")
    if plan.quantity != 1 or gate.quantity != 1:
        blockers.append("max_launch_attempts_requires_quantity_one")
    if not plan.selected_candidate or not plan.selected_region:
        blockers.append("selected_candidate_or_region_missing")

    status: LambdaM051OneShotArmingStatus = (
        "armed_for_one_shot_m051_metadata_bootstrap"
        if not blockers
        else "not_armed"
    )
    arming_id = "m051-one-shot-" + _hash_json(
        {
            "created_at_utc": format_utc(created),
            "expires_at_utc": format_utc(expires),
            "operator_confirmation_hash": confirmation.confirmation_hash,
            "metadata_plan_hash": artifact_hashes.get("metadata_plan"),
            "selected_candidate": plan.selected_candidate,
            "selected_region": plan.selected_region,
        }
    )[:16]
    return LambdaM051OneShotArming(
        arming_id=arming_id,
        arming_status=status,
        created_at_utc=format_utc(created),
        expires_at_utc=format_utc(expires),
        workdir=workdir,
        selected_candidate=plan.selected_candidate,
        selected_region=plan.selected_region,
        operator_confirmation_hash=confirmation.confirmation_hash,
        metadata_plan_hash=artifact_hashes.get("metadata_plan"),
        execution_gate_hash=artifact_hashes.get("execution_gate"),
        no_mutation_no_ssh_audit_hash=artifact_hashes.get("no_mutation_no_ssh_audit"),
        bootstrap_authorization_hash=artifact_hashes.get("bootstrap_authorization"),
        response_loss_controls_hash=artifact_hashes.get("response_loss_controls"),
        artifact_hashes=artifact_hashes,
        artifact_paths=artifact_paths,
        blockers=sorted(set(blockers)),
        warnings=[
            "M051A does not execute launch; reviewer bridge may expose one-shot permission",
            "standing launch_ready and launch_allowed remain false",
        ],
    )


def is_m051_one_shot_arming_expired(
    arming: LambdaM051OneShotArming,
    *,
    now_utc: str | None = None,
) -> bool:
    now = parse_utc(now_utc) if now_utc else datetime.now(timezone.utc)
    return now > parse_utc(arming.expires_at_utc)


def parse_utc(value: str) -> datetime:
    text = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def format_utc(value: datetime) -> str:
    return (
        value.astimezone(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _hash_json(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def load_lambda_m051_one_shot_arming(path: str | Path) -> LambdaM051OneShotArming:
    return LambdaM051OneShotArming.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_m051_one_shot_arming(
    path: str | Path,
    report: LambdaM051OneShotArming,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
