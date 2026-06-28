"""Combined M029 first-launch attempt report."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.mutation_transport_diagnostics import (
    LambdaMutationTransportDiagnostics,
)
from decodilo.lambda_cloud.real_launch_result import (
    LambdaM029LaunchResult,
    LambdaM029TerminationResult,
    redact_instance_id,
)
from decodilo.lambda_cloud.real_launch_spend_audit import LambdaM029SpendAuditReport


class LambdaM029Report(BaseModel):
    model_config = ConfigDict(frozen=True)

    report_schema_version: int = 1
    run_id: str
    real_lambda_api_used: bool
    launch_request_sent: bool
    launch_response_received: bool
    owned_instance_id_redacted: str | None = None
    readonly_verify_running_result: str | None = None
    termination_request_sent: bool
    termination_response_received: bool
    readonly_verify_terminated_result: str | None = None
    termination_verified: bool
    manual_review_required: bool
    mutating_operations: int
    billable_action_performed: bool
    estimated_spend: float
    max_budget: float = 50.0
    max_runtime_minutes: int = 30
    elapsed_seconds: float
    launch_timeout_seconds_effective: float | None = None
    terminate_timeout_seconds_effective: float | None = None
    read_only_verification_timeout_seconds_effective: float | None = None
    no_auto_launch_retry: bool | None = None
    response_capture_lock_hash: str | None = None
    response_capture_active: bool = False
    status_before_parse: bool | None = None
    body_sample_enabled: bool | None = None
    endpoint_confirmation_hash: str | None = None
    endpoint_confirmation_status: str | None = None
    correlation_plan_hash: str | None = None
    launch_idempotency_key_hash: str | None = None
    reconciliation_plan_hash: str | None = None
    candidate_confidence: str | None = None
    terminate_allowed: bool | None = None
    m034_authorization_hash: str | None = None
    third_go_no_go_hash: str | None = None
    m033_report_hash: str | None = None
    launch_response_http_status: int | None = None
    launch_response_content_type: str | None = None
    launch_response_body_size_bytes: int | None = None
    launch_response_classification: str | None = None
    launch_response_error_message_redacted: str | None = None
    termination_response_http_status: int | None = None
    termination_response_content_type: str | None = None
    termination_response_body_size_bytes: int | None = None
    termination_response_classification: str | None = None
    termination_response_error_message_redacted: str | None = None
    launch_outcome: str | None = None
    termination_required: bool | None = None
    ownership_uncertain: bool | None = None
    manual_review_required_for_teardown: bool | None = None
    lower_cost_path_used: bool = False
    capacity_selected_path_used: bool = False
    metadata_bootstrap_path_used: bool = False
    ssh_connectivity_path_used: bool = False
    selected_shape: str | None = None
    selected_candidate: str | None = None
    selected_candidate_source: str | None = None
    selected_region: str | None = None
    selected_ssh_key_hash: str | None = None
    strand_payload_compatible: bool | None = None
    metadata_only: bool | None = None
    metadata_collected: dict[str, Any] = Field(default_factory=dict)
    ssh_attempted: bool = False
    host_discovery_attempted: bool = False
    host_discovery_status: str | None = None
    host_discovery_source: str | None = None
    host_discovery_source_path: str | None = None
    host_discovery_poll_count: int = 0
    host_discovery_duration_seconds: float = 0.0
    ssh_host_present: bool = False
    ssh_key_present: bool | None = None
    ssh_auth_result: str | None = None
    ssh_port_readiness_attempted: bool = False
    ssh_port_reachable: bool | None = None
    ssh_port_poll_count: int = 0
    ssh_port_wait_seconds: float = 0.0
    ssh_port_connect_timeout_seconds: float | None = None
    ssh_exit_status: int | None = None
    ssh_failure_classification: str | None = None
    ssh_redacted_stderr_present: bool = False
    ssh_stderr_sha256_prefix: str | None = None
    ssh_stderr_truncated: bool = False
    ssh_stderr_secret_scan_passed: bool | None = None
    remote_command_attempted: bool = False
    remote_command: str | None = None
    remote_command_result: str | None = None
    remote_command_stage_results: list[dict[str, Any]] = Field(default_factory=list)
    command_manifest_hash: str | None = None
    max_remote_commands: int | None = None
    stop_on_first_failure: bool | None = None
    vertical_slice_status: str | None = None
    failed_stage: str | None = None
    source_bundle_upload_attempted: bool = False
    source_bundle_upload_succeeded: bool = False
    source_bundle_hash_verified: bool = False
    source_bundle_sha256: str | None = None
    source_bundle_remote_path: str | None = None
    dependency_bundle_upload_attempted: bool = False
    dependency_bundle_upload_succeeded: bool = False
    dependency_bundle_hash_verified: bool = False
    dependency_bundle_sha256: str | None = None
    dependency_bundle_remote_path: str | None = None
    uploaded_bundles_count: int = 0
    local_dependency_install_attempted: bool = False
    local_dependency_install_succeeded: bool = False
    experiment_output_artifact_capture_attempted: bool = False
    experiment_output_artifact_capture_succeeded: bool = False
    experiment_output_artifact_path: str | None = None
    experiment_output_artifact_exists: bool = False
    experiment_output_artifact_bytes: int | None = None
    experiment_output_artifact_sha256: str | None = None
    experiment_output_artifact_secret_scan_passed: bool | None = None
    experiment_output_artifact_body_capture_attempted: bool = False
    experiment_output_artifact_body_capture_succeeded: bool = False
    experiment_output_artifact_body_persisted: bool = False
    experiment_output_artifact_body_json: dict[str, Any] | None = None
    experiment_output_artifact_parsed_summary_persisted: bool = False
    experiment_output_artifact_parsed_summary: dict[str, Any] | None = None
    experiment_output_artifact_parse_status: str | None = None
    experiment_output_artifact_content_capture_status: str | None = None
    command_output_collected: bool = False
    stdout_capture_active: bool = False
    stdout_redacted_present: bool = False
    stdout_sha256_prefix: str | None = None
    stdout_truncated: bool = False
    stdout_secret_scan_passed: bool | None = None
    file_transfer_attempted: bool = False
    port_forwarding_attempted: bool = False
    package_install_attempted: bool = False
    downloads_attempted: bool = False
    training_attempted: bool = False
    old_path_fallback_blocked: bool = False
    m039_path_fallback_blocked: bool = False
    launch_ready: bool = False
    launch_allowed: bool = False
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _completion_flags(self) -> LambdaM029Report:
        if self.launch_ready or self.launch_allowed:
            raise ValueError("M029 report must leave launch flags false after completion")
        if self.max_budget > 50 or self.max_runtime_minutes > 30:
            raise ValueError("M029 report exceeds hard limits")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_m029_report(
    *,
    run_id: str,
    launch_result: LambdaM029LaunchResult | None,
    termination_result: LambdaM029TerminationResult | None,
    spend_audit: LambdaM029SpendAuditReport,
    elapsed_seconds: float,
    real_lambda_api_used: bool = False,
    m034_gate_check: Any | None = None,
    transport_diagnostics: Sequence[LambdaMutationTransportDiagnostics] | None = None,
) -> LambdaM029Report:
    launch_sent = bool(launch_result and launch_result.request_sent)
    terminate_sent = bool(termination_result and termination_result.request_sent)
    termination_verified = bool(termination_result and termination_result.termination_verified)
    owned_id = None
    if launch_result and launch_result.owned_instance_id:
        owned_id = launch_result.owned_instance_id
    elif termination_result:
        owned_id = termination_result.owned_instance_id
    manual_review = bool(
        (launch_result and launch_result.manual_review_required)
        or (termination_result and termination_result.manual_review_required)
        or (launch_sent and not termination_verified)
    )
    gate = _gate_fields(m034_gate_check)
    launch_capture = _capture_fields(transport_diagnostics, "launch_one_instance")
    terminate_capture = _capture_fields(
        transport_diagnostics,
        "terminate_owned_instance",
    )
    capacity_semantics = _capacity_semantic_fields(
        launch_sent=launch_sent,
        owned_id=owned_id,
        launch_capture=launch_capture,
    )
    return LambdaM029Report(
        run_id=run_id,
        real_lambda_api_used=real_lambda_api_used,
        launch_request_sent=launch_sent,
        launch_response_received=bool(launch_result and launch_result.response_received),
        owned_instance_id_redacted=redact_instance_id(owned_id),
        readonly_verify_running_result=(
            launch_result.lifecycle_state if launch_result else None
        ),
        termination_request_sent=terminate_sent,
        termination_response_received=bool(
            termination_result and termination_result.response_received
        ),
        readonly_verify_terminated_result=(
            termination_result.lifecycle_state if termination_result else None
        ),
        termination_verified=termination_verified,
        manual_review_required=manual_review,
        mutating_operations=int(launch_sent) + int(terminate_sent),
        billable_action_performed=spend_audit.billable_action_performed,
        estimated_spend=spend_audit.estimated_spend,
        elapsed_seconds=elapsed_seconds,
        **gate,
        **launch_capture,
        **terminate_capture,
        **capacity_semantics,
        warnings=[
            *(launch_result.warnings if launch_result else []),
            *(termination_result.warnings if termination_result else []),
            *spend_audit.warnings,
        ],
        errors=[
            *(launch_result.errors if launch_result else []),
            *(termination_result.errors if termination_result else []),
            *spend_audit.errors,
        ],
    )


def _gate_fields(gate: Any | None) -> dict[str, Any]:
    if gate is None:
        return {}
    data = gate.model_dump(mode="json") if hasattr(gate, "model_dump") else dict(gate)
    return {
        "launch_timeout_seconds_effective": data.get("effective_launch_timeout_seconds"),
        "terminate_timeout_seconds_effective": data.get(
            "effective_terminate_timeout_seconds"
        ),
        "read_only_verification_timeout_seconds_effective": data.get(
            "effective_read_only_verification_timeout_seconds"
        ),
        "no_auto_launch_retry": data.get("no_auto_launch_retry"),
        "response_capture_lock_hash": data.get("response_capture_lock_hash"),
        "response_capture_active": bool(data.get("response_capture_active")),
        "status_before_parse": data.get("status_before_parse"),
        "body_sample_enabled": data.get("body_sample_enabled"),
        "endpoint_confirmation_hash": data.get("endpoint_confirmation_hash"),
        "endpoint_confirmation_status": data.get("endpoint_confirmation_status"),
        "correlation_plan_hash": data.get("correlation_plan_hash"),
        "launch_idempotency_key_hash": data.get("launch_idempotency_key_hash"),
        "reconciliation_plan_hash": data.get("reconciliation_plan_hash"),
        "candidate_confidence": data.get("candidate_confidence"),
        "terminate_allowed": data.get("terminate_allowed"),
        "m034_authorization_hash": data.get("m034_authorization_hash"),
        "third_go_no_go_hash": data.get("third_go_no_go_hash"),
        "m033_report_hash": data.get("m033_report_hash"),
        "lower_cost_path_used": bool(data.get("lower_cost_path_used")),
        "capacity_selected_path_used": bool(data.get("capacity_selected_path_used")),
        "metadata_bootstrap_path_used": bool(
            data.get("metadata_bootstrap_path_used")
        ),
        "ssh_connectivity_path_used": bool(data.get("ssh_connectivity_path_used")),
        "selected_shape": data.get("selected_shape") or data.get("selected_candidate"),
        "selected_candidate": data.get("selected_candidate"),
        "selected_candidate_source": data.get("selected_candidate_source"),
        "selected_region": data.get("selected_region"),
        "selected_ssh_key_hash": data.get("selected_ssh_key_hash"),
        "strand_payload_compatible": data.get("strand_payload_compatible"),
        "metadata_only": data.get("metadata_only"),
        "metadata_collected": data.get("metadata_collected") or {},
        "ssh_attempted": bool(data.get("ssh_attempted")),
        "remote_command_attempted": bool(data.get("remote_command_attempted")),
        "package_install_attempted": bool(data.get("package_install_attempted")),
        "training_attempted": bool(data.get("training_attempted")),
        "old_path_fallback_blocked": bool(data.get("old_path_fallback_blocked")),
        "m039_path_fallback_blocked": bool(data.get("m039_path_fallback_blocked")),
    }


def _capture_fields(
    diagnostics: Sequence[LambdaMutationTransportDiagnostics] | None,
    operation: str,
) -> dict[str, Any]:
    prefix = "launch" if operation == "launch_one_instance" else "termination"
    for item in reversed(list(diagnostics or [])):
        if item.operation == operation and item.response_capture is not None:
            metadata = item.response_capture.metadata
            return {
                f"{prefix}_response_http_status": metadata.status_code,
                f"{prefix}_response_content_type": metadata.content_type,
                f"{prefix}_response_body_size_bytes": metadata.body_size_bytes,
                f"{prefix}_response_classification": item.response_capture.classification,
                f"{prefix}_response_error_message_redacted": (
                    metadata.provider_error_message_redacted
                ),
            }
    return {}


def _capacity_semantic_fields(
    *,
    launch_sent: bool,
    owned_id: str | None,
    launch_capture: dict[str, Any],
) -> dict[str, Any]:
    message = launch_capture.get("launch_response_error_message_redacted")
    capacity_rejected = (
        launch_sent
        and launch_capture.get("launch_response_http_status") == 400
        and launch_capture.get("launch_response_classification") == "http_error_json"
        and not owned_id
        and isinstance(message, str)
        and "capacity" in message.lower()
    )
    if capacity_rejected:
        return {
            "launch_outcome": "capacity_rejected_no_instance_created",
            "termination_required": False,
            "ownership_uncertain": False,
            "manual_review_required_for_teardown": False,
        }
    if launch_sent and not owned_id:
        return {
            "launch_outcome": "ambiguous_launch_no_owned_instance_id",
            "termination_required": False,
            "ownership_uncertain": True,
            "manual_review_required_for_teardown": True,
        }
    return {
        "launch_outcome": None,
        "termination_required": bool(owned_id),
        "ownership_uncertain": False,
        "manual_review_required_for_teardown": None,
    }


def load_lambda_m029_report(path: str | Path) -> LambdaM029Report:
    return LambdaM029Report.model_validate_json(Path(path).read_text("utf-8"))


def write_lambda_m029_report(path: str | Path, report: LambdaM029Report) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
