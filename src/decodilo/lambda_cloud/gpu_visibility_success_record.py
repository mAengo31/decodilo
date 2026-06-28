"""Success record for the completed M063 GPU visibility query run."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from decodilo.lambda_cloud.gpu_visibility_command_policy import (
    M063_GPU_VISIBILITY_COMMAND,
)
from decodilo.lambda_cloud.live_discovery_report import load_lambda_live_discovery_report
from decodilo.lambda_cloud.m029_report import load_lambda_m029_report
from decodilo.lambda_cloud.real_launch_spend_audit import LambdaM029SpendAuditReport

DEFAULT_M063_FINAL_DISCOVERY = Path("/tmp/decodilo-lambda-post-m063-discovery.json")

LambdaGPUVisibilitySuccessStatus = Literal[
    "gpu_visibility_query_success",
    "gpu_visibility_query_executed_output_hash_only",
    "gpu_visibility_query_partial",
    "gpu_visibility_query_failed",
]


class LambdaGPUVisibilitySuccessRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    record_schema_version: int = 1
    milestone: str = "M063"
    run_id: str
    source_workdir: str
    final_discovery_path: str
    selected_candidate: str | None = None
    selected_region: str | None = None
    owned_instance_id_redacted: str | None = None
    launch_request_sent: bool
    launch_response_received: bool
    launch_status_code: int | None = None
    running_verification: str | None = None
    host_discovery_result: str | None = None
    host_discovery_source_path: str | None = None
    tcp_22_readiness_result: bool | None = None
    ssh_attempted: bool
    ssh_auth_success: bool
    command_executed: bool
    command: str = M063_GPU_VISIBILITY_COMMAND
    command_category: str = "gpu_visibility_query"
    command_exit_code: int | None = None
    stdout_captured: bool
    stdout_redacted: bool
    stdout_hash_prefix: str | None = None
    parsed_gpu_name: str | None = None
    parsed_memory_total: str | None = None
    parsed_driver_version: str | None = None
    parsed_fields_present: bool
    raw_stdout_reported: bool
    stderr_captured_redacted: bool
    file_transfer_attempted: bool
    port_forwarding_attempted: bool
    package_install_attempted: bool
    training_attempted: bool
    termination_request_sent: bool
    termination_verified: bool
    final_instance_count: int
    final_unmanaged_count: int
    manual_review_required: bool
    mutating_operations: int
    historical_billable_action_performed: bool
    estimated_spend: float
    conservative_spend: float | None = None
    secret_scan_passed: bool
    status: LambdaGPUVisibilitySuccessStatus
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    launch_ready: bool = False
    launch_allowed: bool = False
    billable_action_performed: bool = False
    real_mutation_enabled: bool = False

    @model_validator(mode="after")
    def _validate_closeout_only(self) -> LambdaGPUVisibilitySuccessRecord:
        if (
            self.launch_ready
            or self.launch_allowed
            or self.billable_action_performed
            or self.real_mutation_enabled
        ):
            raise ValueError("M064 success record cannot enable launch or mutation")
        if (
            self.command != M063_GPU_VISIBILITY_COMMAND
            or self.command_category != "gpu_visibility_query"
        ):
            raise ValueError("M064 success record can only classify the M063 GPU query")
        if self.status == "gpu_visibility_query_success" and not self.parsed_fields_present:
            raise ValueError("full GPU visibility success requires parsed fields")
        if self.status in {
            "gpu_visibility_query_success",
            "gpu_visibility_query_executed_output_hash_only",
        } and (
            self.raw_stdout_reported
            or self.file_transfer_attempted
            or self.port_forwarding_attempted
            or self.package_install_attempted
            or self.training_attempted
        ):
            raise ValueError("successful M063 GPU record includes forbidden work")
        return self

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def build_lambda_gpu_visibility_success_record_from_paths(
    *,
    workdir: str | Path,
    final_discovery: str | Path | None = None,
) -> LambdaGPUVisibilitySuccessRecord:
    workdir_path = Path(workdir)
    discovery_path = Path(final_discovery or DEFAULT_M063_FINAL_DISCOVERY)
    report = load_lambda_m029_report(workdir_path / "report.json")
    discovery = load_lambda_live_discovery_report(discovery_path)
    evidence_path = workdir_path / "ssh-connectivity-evidence.json"
    evidence = _load_json(evidence_path)
    spend_path = workdir_path / "spend-audit.json"
    spend = (
        LambdaM029SpendAuditReport.model_validate_json(
            spend_path.read_text(encoding="utf-8")
        )
        if spend_path.exists()
        else None
    )
    conservative = None if spend is None else spend.estimated_spend
    final_instance_count = len(discovery.instances)
    final_unmanaged_count = len(discovery.unmanaged_instances)
    secret_scan_passed = _strict_secret_scan_passed(
        [
            workdir_path / "report.json",
            workdir_path / "ssh-connectivity-evidence.json",
            workdir_path / "ssh-host-discovery.json",
            workdir_path / "transport-diagnostics.json",
            discovery_path,
        ]
    )
    raw_stdout_reported = bool(
        evidence.get("stdout_stored")
        or evidence.get("stdout_raw")
        or evidence.get("stdout")
        or evidence.get("raw_stdout")
    )
    parsed = _extract_parsed_gpu_fields(report.metadata_collected, evidence)
    parsed_fields_present = all(parsed.values())
    stdout_redacted = (
        report.stdout_redacted_present
        and report.stdout_secret_scan_passed is True
        and evidence.get("stdout_redacted") == "<redacted-gpu-visibility>"
        and not raw_stdout_reported
    )
    blockers: list[str] = []
    if report.run_id != "lambda-m063-gpu-visibility-query":
        blockers.append("m063_run_id_not_confirmed")
    if not report.launch_request_sent:
        blockers.append("launch_request_not_sent")
    if not report.launch_response_received:
        blockers.append("launch_response_not_received")
    if report.launch_response_http_status != 200:
        blockers.append("launch_status_not_success")
    if report.readonly_verify_running_result != "running":
        blockers.append("running_verification_not_running")
    if report.host_discovery_status != "FOUND":
        blockers.append("host_discovery_not_found")
    if report.ssh_port_reachable is not True:
        blockers.append("tcp_22_not_reachable")
    if not report.ssh_attempted:
        blockers.append("ssh_not_attempted")
    if report.ssh_auth_result != "remote_command_succeeded":
        blockers.append("ssh_command_not_successful")
    if not report.remote_command_attempted:
        blockers.append("remote_command_not_attempted")
    if report.remote_command != M063_GPU_VISIBILITY_COMMAND:
        blockers.append("remote_command_not_exact_gpu_visibility_query")
    if report.remote_command_result != "succeeded":
        blockers.append("remote_command_not_succeeded")
    if report.ssh_exit_status != 0:
        blockers.append("command_exit_code_not_zero")
    if evidence.get("approved_command") != M063_GPU_VISIBILITY_COMMAND:
        blockers.append("approved_command_not_exact_gpu_visibility_query")
    if evidence.get("command_output_collected") is not True:
        blockers.append("gpu_visibility_stdout_not_collected")
    if not stdout_redacted:
        blockers.append("gpu_visibility_stdout_not_redacted")
    if raw_stdout_reported:
        blockers.append("raw_stdout_reported")
    if not report.ssh_redacted_stderr_present:
        blockers.append("redacted_stderr_not_captured")
    if report.file_transfer_attempted:
        blockers.append("file_transfer_attempted")
    if report.port_forwarding_attempted:
        blockers.append("port_forwarding_attempted")
    if report.package_install_attempted:
        blockers.append("package_install_attempted")
    if report.training_attempted:
        blockers.append("training_attempted")
    if not report.termination_request_sent:
        blockers.append("termination_request_not_sent")
    if not report.termination_verified:
        blockers.append("termination_not_verified")
    if report.manual_review_required:
        blockers.append("manual_review_required")
    if final_instance_count != 0:
        blockers.append("final_instance_count_nonzero")
    if final_unmanaged_count != 0:
        blockers.append("final_unmanaged_count_nonzero")
    if report.estimated_spend >= 50 or (conservative is not None and conservative >= 50):
        blockers.append("estimated_spend_not_below_budget")
    if not secret_scan_passed:
        blockers.append("secret_scan_not_passed")
    if not blockers and parsed_fields_present:
        status: LambdaGPUVisibilitySuccessStatus = "gpu_visibility_query_success"
    elif not blockers and report.stdout_sha256_prefix:
        status = "gpu_visibility_query_executed_output_hash_only"
    elif report.launch_request_sent and report.termination_request_sent:
        status = "gpu_visibility_query_partial"
    else:
        status = "gpu_visibility_query_failed"
    warnings = [
        "M064 records historical M063 billable action only",
        "M064 performs no Lambda, SSH, or remote command operation",
    ]
    if status == "gpu_visibility_query_executed_output_hash_only":
        warnings.append("M063 persisted redacted stdout hash only; parsed GPU fields absent")
    return LambdaGPUVisibilitySuccessRecord(
        run_id=report.run_id,
        source_workdir=str(workdir_path),
        final_discovery_path=str(discovery_path),
        selected_candidate=report.selected_candidate or report.selected_shape,
        selected_region=report.selected_region,
        owned_instance_id_redacted=report.owned_instance_id_redacted,
        launch_request_sent=report.launch_request_sent,
        launch_response_received=report.launch_response_received,
        launch_status_code=report.launch_response_http_status,
        running_verification=report.readonly_verify_running_result,
        host_discovery_result=report.host_discovery_status,
        host_discovery_source_path=report.host_discovery_source_path,
        tcp_22_readiness_result=report.ssh_port_reachable,
        ssh_attempted=report.ssh_attempted,
        ssh_auth_success=report.ssh_auth_result == "remote_command_succeeded",
        command_executed=report.remote_command_attempted,
        command_exit_code=report.ssh_exit_status,
        stdout_captured=bool(report.command_output_collected),
        stdout_redacted=stdout_redacted,
        stdout_hash_prefix=report.stdout_sha256_prefix,
        parsed_gpu_name=parsed["gpu_name"],
        parsed_memory_total=parsed["memory_total"],
        parsed_driver_version=parsed["driver_version"],
        parsed_fields_present=parsed_fields_present,
        raw_stdout_reported=raw_stdout_reported,
        stderr_captured_redacted=bool(report.ssh_redacted_stderr_present),
        file_transfer_attempted=report.file_transfer_attempted,
        port_forwarding_attempted=report.port_forwarding_attempted,
        package_install_attempted=report.package_install_attempted,
        training_attempted=report.training_attempted,
        termination_request_sent=report.termination_request_sent,
        termination_verified=report.termination_verified,
        final_instance_count=final_instance_count,
        final_unmanaged_count=final_unmanaged_count,
        manual_review_required=report.manual_review_required,
        mutating_operations=report.mutating_operations,
        historical_billable_action_performed=report.billable_action_performed,
        estimated_spend=report.estimated_spend,
        conservative_spend=conservative,
        secret_scan_passed=secret_scan_passed,
        status=status,
        blockers=sorted(set(blockers)),
        warnings=warnings,
    )


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _extract_parsed_gpu_fields(
    metadata: dict[str, Any],
    evidence: dict[str, Any],
) -> dict[str, str | None]:
    candidates: list[dict[str, Any]] = [metadata, evidence]
    for key in (
        "gpu_visibility",
        "gpu_visibility_fields",
        "parsed_gpu_fields",
        "parsed_stdout_fields",
    ):
        for source in (metadata, evidence):
            value = source.get(key)
            if isinstance(value, dict):
                candidates.append(value)
    return {
        "gpu_name": _first_string(
            candidates,
            ("parsed_gpu_name", "gpu_name", "name"),
        ),
        "memory_total": _first_string(
            candidates,
            ("parsed_memory_total", "memory_total", "memory.total"),
        ),
        "driver_version": _first_string(
            candidates,
            ("parsed_driver_version", "driver_version"),
        ),
    }


def _first_string(sources: list[dict[str, Any]], keys: tuple[str, ...]) -> str | None:
    for source in sources:
        for key in keys:
            value = source.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _strict_secret_scan_passed(paths: list[Path]) -> bool:
    checks = [
        re.compile(r"Authorization\s*:", re.I),
        re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]{8,}", re.I),
        re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
        re.compile(r"LAMBDA_API_KEY\s*="),
        re.compile(r"api[_-]?key\s*[=:]\s*[A-Za-z0-9._~+/=-]{8,}", re.I),
        re.compile(r"password\s*[=:]\s*[^\s,}\]]+", re.I),
    ]
    for path in paths:
        if not path.exists() or not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if any(check.search(text) for check in checks):
            return False
    return True


def load_lambda_gpu_visibility_success_record(
    path: str | Path,
) -> LambdaGPUVisibilitySuccessRecord:
    return LambdaGPUVisibilitySuccessRecord.model_validate_json(
        Path(path).read_text(encoding="utf-8")
    )


def write_lambda_gpu_visibility_success_record(
    path: str | Path,
    report: LambdaGPUVisibilitySuccessRecord,
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report.to_json(), encoding="utf-8")
