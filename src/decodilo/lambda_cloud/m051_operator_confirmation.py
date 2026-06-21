"""Immediate operator confirmation for M051 one-shot metadata bootstrap."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

LambdaM051OperatorConfirmationStatus = Literal[
    "not_provided",
    "confirmed_for_m051_one_shot_metadata_bootstrap",
]

_FORBIDDEN_STATUSES = {
    "launch_now",
    "launch_ready",
    "launch_allowed",
    "background_execution_allowed",
    "unattended_execution_allowed",
}


class LambdaM051OperatorConfirmation(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    confirmation_status: LambdaM051OperatorConfirmationStatus
    confirmation_hash: str | None = None
    present_for_m051_metadata_only_attempt: bool = False
    billable_instance_acknowledged: bool = False
    exactly_one_launch_attempt_approved: bool = False
    metadata_only_bootstrap_approved: bool = False
    no_ssh_acknowledged: bool = False
    no_remote_commands_acknowledged: bool = False
    no_setup_scripts_acknowledged: bool = False
    no_cloud_init_acknowledged: bool = False
    no_package_installs_acknowledged: bool = False
    no_training_acknowledged: bool = False
    no_restart_create_delete_acknowledged: bool = False
    max_budget_approved: float = 50.0
    max_runtime_minutes_approved: int = 30
    existing_ssh_key_payload_only_acknowledged: bool = False
    no_auto_retry_acknowledged: bool = False
    owned_instance_termination_acknowledged: bool = False
    termination_verification_acknowledged: bool = False
    os_shutdown_insufficient_acknowledged: bool = False
    operator_remains_available_acknowledged: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_safe_status(self) -> LambdaM051OperatorConfirmation:
        if str(self.confirmation_status) in _FORBIDDEN_STATUSES:
            raise ValueError("M051 operator confirmation cannot authorize execution")
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M051 operator confirmation must keep launch disabled")
        if self.confirmation_status == "confirmed_for_m051_one_shot_metadata_bootstrap":
            if self.blockers:
                raise ValueError("confirmed M051 operator confirmation cannot have blockers")
            if not self.confirmation_hash:
                raise ValueError("confirmed M051 operator confirmation requires a hash")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m051_operator_confirmation(
    *,
    confirm_metadata_only_bootstrap: bool,
    acknowledge_all: bool,
) -> LambdaM051OperatorConfirmation:
    acknowledgements = {
        "present_for_m051_metadata_only_attempt": (
            confirm_metadata_only_bootstrap and acknowledge_all
        ),
        "billable_instance_acknowledged": acknowledge_all,
        "exactly_one_launch_attempt_approved": acknowledge_all,
        "metadata_only_bootstrap_approved": (
            confirm_metadata_only_bootstrap and acknowledge_all
        ),
        "no_ssh_acknowledged": acknowledge_all,
        "no_remote_commands_acknowledged": acknowledge_all,
        "no_setup_scripts_acknowledged": acknowledge_all,
        "no_cloud_init_acknowledged": acknowledge_all,
        "no_package_installs_acknowledged": acknowledge_all,
        "no_training_acknowledged": acknowledge_all,
        "no_restart_create_delete_acknowledged": acknowledge_all,
        "existing_ssh_key_payload_only_acknowledged": acknowledge_all,
        "no_auto_retry_acknowledged": acknowledge_all,
        "owned_instance_termination_acknowledged": acknowledge_all,
        "termination_verification_acknowledged": acknowledge_all,
        "os_shutdown_insufficient_acknowledged": acknowledge_all,
        "operator_remains_available_acknowledged": acknowledge_all,
    }
    blockers = [
        name
        for name, value in acknowledgements.items()
        if not value
    ]
    status: LambdaM051OperatorConfirmationStatus = (
        "confirmed_for_m051_one_shot_metadata_bootstrap"
        if not blockers
        else "not_provided"
    )
    material = {
        **acknowledgements,
        "max_budget_approved": 50.0,
        "max_runtime_minutes_approved": 30,
        "confirmation_status": status,
    }
    confirmation_hash = (
        hashlib.sha256(
            json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        if status == "confirmed_for_m051_one_shot_metadata_bootstrap"
        else None
    )
    return LambdaM051OperatorConfirmation(
        confirmation_status=status,
        confirmation_hash=confirmation_hash,
        max_budget_approved=50.0,
        max_runtime_minutes_approved=30,
        blockers=sorted(blockers),
        warnings=[
            "operator confirmation is immediate and one-shot scoped",
            "standing launch_ready and launch_allowed remain false",
        ],
        **acknowledgements,
    )


def load_lambda_m051_operator_confirmation(
    path: str | Path,
) -> LambdaM051OperatorConfirmation:
    return LambdaM051OperatorConfirmation.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_m051_operator_confirmation(
    path: str | Path,
    report: LambdaM051OperatorConfirmation,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
