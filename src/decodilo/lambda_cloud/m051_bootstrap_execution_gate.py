"""Execution gate for the M051 metadata-only Lambda bootstrap path."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.bootstrap_risk_review import (
    load_lambda_bootstrap_risk_review,
)
from decodilo.lambda_cloud.m051_bootstrap_authorization import (
    load_lambda_m051_bootstrap_authorization,
)
from decodilo.lambda_cloud.m051_metadata_bootstrap_plan import (
    load_lambda_m051_metadata_bootstrap_plan,
)
from decodilo.lambda_cloud.remote_access_policy import load_lambda_remote_access_policy
from decodilo.lambda_cloud.remote_bootstrap_scope import load_lambda_remote_bootstrap_scope
from decodilo.lambda_cloud.strand_response_loss_control_check import (
    load_lambda_strand_response_loss_control_check,
)


class LambdaM051BootstrapExecutionGate(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    gate_passed: bool
    selected_candidate: str | None = None
    selected_region: str | None = None
    selected_ssh_key_hash: str | None = None
    metadata_only: bool = True
    ssh_used: bool = False
    remote_commands_allowed: bool = False
    package_install_allowed: bool = False
    training_allowed: bool = False
    setup_scripts_allowed: bool = False
    cloud_init_allowed: bool = False
    quantity: int = 1
    raw_ssh_key_required_for_payload: bool = True
    response_capture_active: bool
    status_before_parse: bool
    no_auto_launch_retry: bool
    strand_payload_compatible: bool
    effective_launch_timeout_seconds: float | None = None
    effective_terminate_timeout_seconds: float | None = None
    effective_read_only_verification_timeout_seconds: float | None = None
    metadata_bootstrap_path_used: bool = True
    metadata_collected: dict[str, object] = Field(default_factory=dict)
    ssh_attempted: bool = False
    remote_command_attempted: bool = False
    package_install_attempted: bool = False
    training_attempted: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_disabled(self) -> LambdaM051BootstrapExecutionGate:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
            or self.ssh_used
            or self.remote_commands_allowed
            or self.package_install_allowed
            or self.training_allowed
            or self.setup_scripts_allowed
            or self.cloud_init_allowed
        ):
            raise ValueError("M051 bootstrap execution gate cannot enable unsafe work")
        if self.gate_passed and self.blockers:
            raise ValueError("M051 bootstrap execution gate cannot pass with blockers")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_m051_bootstrap_execution_gate_from_paths(
    *,
    metadata_plan: str | Path,
    scope: str | Path,
    access_policy: str | Path,
    risk_review: str | Path,
    authorization: str | Path,
    response_loss_controls: str | Path,
) -> LambdaM051BootstrapExecutionGate:
    plan = load_lambda_m051_metadata_bootstrap_plan(metadata_plan)
    scope_report = load_lambda_remote_bootstrap_scope(scope)
    access = load_lambda_remote_access_policy(access_policy)
    risk = load_lambda_bootstrap_risk_review(risk_review)
    auth = load_lambda_m051_bootstrap_authorization(authorization)
    controls = load_lambda_strand_response_loss_control_check(response_loss_controls)

    blockers = [
        *plan.blockers,
        *scope_report.blockers,
        *access.blockers,
        *risk.blockers,
        *auth.blockers,
        *controls.blockers,
    ]
    if not plan.plan_passed:
        blockers.append("metadata_bootstrap_plan_not_passed")
    if scope_report.default_experiment_type != "lifecycle_plus_metadata_only":
        blockers.append("scope_is_not_metadata_only")
    if access.default_access_mode != "provider_metadata_only":
        blockers.append("access_policy_not_provider_metadata_only")
    if (
        access.ssh_allowed_without_operator_approval
        or access.ssh_key_attachment_implies_ssh_approval
        or access.interactive_shell_allowed
        or access.arbitrary_shell_allowed
        or access.file_transfer_allowed
        or access.background_command_allowed
    ):
        blockers.append("remote_access_policy_allows_ssh_or_commands")
    if not risk.risk_review_passed:
        blockers.append("bootstrap_risk_review_not_passed")
    if risk.selected_bootstrap_mode != "lifecycle_plus_metadata_only":
        blockers.append("risk_review_mode_is_not_metadata_only")
    if risk.ssh_approval_status != "declined_no_ssh":
        blockers.append("ssh_must_be_declined_for_metadata_only_bootstrap")
    if risk.command_allowlist_status != "allowlist_defined_future_only":
        blockers.append("command_allowlist_not_future_only")
    if risk.package_install_policy_status != "package_install_denied":
        blockers.append("package_install_policy_not_denied")
    if risk.no_training_policy_status != "training_denied":
        blockers.append("training_policy_not_denied")
    if auth.authorization_status != (
        "authorized_for_future_m051_metadata_only_bootstrap_review"
    ):
        blockers.append("m051_metadata_authorization_not_ready")
    if not controls.controls_passed:
        blockers.append("response_loss_controls_not_passed")
    if not controls.response_capture_active:
        blockers.append("response_capture_not_active")
    if not controls.status_before_parse:
        blockers.append("status_before_parse_not_enabled")
    if controls.timeout_seconds < 30:
        blockers.append("timeout_seconds_below_30")
    if not controls.no_auto_launch_retry:
        blockers.append("automatic_launch_retry_enabled")
    if not controls.strand_launch_payload_shape_valid:
        blockers.append("strand_payload_shape_invalid")
    if plan.quantity != 1:
        blockers.append("quantity_must_equal_one")
    if plan.ssh_used or plan.remote_commands_allowed:
        blockers.append("metadata_plan_allows_remote_access")
    if plan.package_install_allowed or plan.training_allowed:
        blockers.append("metadata_plan_allows_install_or_training")

    return LambdaM051BootstrapExecutionGate(
        gate_passed=not blockers,
        selected_candidate=plan.selected_candidate,
        selected_region=plan.selected_region,
        selected_ssh_key_hash=plan.selected_ssh_key_hash,
        quantity=plan.quantity,
        response_capture_active=controls.response_capture_active,
        status_before_parse=controls.status_before_parse,
        no_auto_launch_retry=controls.no_auto_launch_retry,
        strand_payload_compatible=plan.strand_payload_compatible
        and controls.strand_launch_payload_shape_valid,
        metadata_collected={
            "instance_type": plan.selected_candidate,
            "region": plan.selected_region,
            "metadata_only": True,
            "source": "lambda_provider_api",
        },
        effective_launch_timeout_seconds=controls.timeout_seconds,
        effective_terminate_timeout_seconds=controls.timeout_seconds,
        effective_read_only_verification_timeout_seconds=controls.timeout_seconds,
        blockers=sorted(set(blockers)),
        warnings=[
            "M051 execution gate is offline until m029 run arms the launch",
            "metadata-only mode permits provider/API metadata collection only",
            "SSH key attachment does not approve SSH use",
        ],
    )


def load_lambda_m051_bootstrap_execution_gate(
    path: str | Path,
) -> LambdaM051BootstrapExecutionGate:
    return LambdaM051BootstrapExecutionGate.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_m051_bootstrap_execution_gate(
    path: str | Path,
    report: LambdaM051BootstrapExecutionGate,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
