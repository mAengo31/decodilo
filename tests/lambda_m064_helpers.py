from __future__ import annotations

import json
from pathlib import Path

from decodilo.lambda_cloud.gpu_visibility_closeout import (
    build_lambda_gpu_visibility_closeout_from_paths,
    write_lambda_gpu_visibility_closeout,
)
from decodilo.lambda_cloud.gpu_visibility_evidence_package import (
    build_lambda_gpu_visibility_evidence_package_from_paths,
    write_lambda_gpu_visibility_evidence_package,
)
from decodilo.lambda_cloud.gpu_visibility_output_policy import (
    build_lambda_gpu_visibility_output_policy,
    write_lambda_gpu_visibility_output_policy,
)
from decodilo.lambda_cloud.gpu_visibility_parsed_output_audit import (
    build_lambda_gpu_visibility_parsed_output_audit_from_paths,
    write_lambda_gpu_visibility_parsed_output_audit,
)
from decodilo.lambda_cloud.gpu_visibility_reconciliation import (
    build_lambda_gpu_visibility_reconciliation_from_paths,
    write_lambda_gpu_visibility_reconciliation,
)
from decodilo.lambda_cloud.gpu_visibility_success_record import (
    build_lambda_gpu_visibility_success_record_from_paths,
    write_lambda_gpu_visibility_success_record,
)
from decodilo.lambda_cloud.live_discovery_report import (
    LambdaLiveDiscoveryReport,
    write_lambda_live_discovery_report,
)
from decodilo.lambda_cloud.m064_report import build_lambda_m064_report_from_paths
from decodilo.lambda_cloud.m065_python_runtime_authorization import (
    build_lambda_m065_python_runtime_authorization_from_paths,
    write_lambda_m065_python_runtime_authorization,
)
from decodilo.lambda_cloud.m065_python_runtime_runbook_preview import (
    build_lambda_m065_python_runtime_runbook_preview_from_path,
    write_lambda_m065_python_runtime_runbook_preview,
)
from decodilo.lambda_cloud.python_runtime_command_policy import (
    build_lambda_python_runtime_command_policy,
    write_lambda_python_runtime_command_policy,
)
from decodilo.lambda_cloud.python_runtime_command_review import (
    build_lambda_python_runtime_command_review_from_paths,
    write_lambda_python_runtime_command_review,
)
from decodilo.lambda_cloud.python_runtime_output_policy import (
    build_lambda_python_runtime_output_policy,
    write_lambda_python_runtime_output_policy,
)
from decodilo.lambda_cloud.real_launch_spend_audit import (
    build_m029_spend_audit,
    write_lambda_m029_spend_audit,
)

GPU_COMMAND = (
    "nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader"
)


def write_m063_gpu_visibility_workdir(
    tmp_path: Path,
    *,
    parsed_fields: bool = False,
    remote_command: str = GPU_COMMAND,
    training_attempted: bool = False,
    final_instance_count: int = 0,
) -> dict[str, Path]:
    workdir = tmp_path / "m063"
    workdir.mkdir(parents=True)
    metadata_collected = {}
    if parsed_fields:
        metadata_collected = {
            "parsed_gpu_fields": {
                "gpu_name": "NVIDIA A10",
                "memory_total": "23028 MiB",
                "driver_version": "550.54.15",
            }
        }
    report = {
        "report_schema_version": 1,
        "run_id": "lambda-m063-gpu-visibility-query",
        "real_lambda_api_used": True,
        "launch_request_sent": True,
        "launch_response_received": True,
        "launch_response_http_status": 200,
        "launch_response_content_type": "application/json",
        "launch_response_body_size_bytes": 63,
        "launch_response_classification": "success_json",
        "owned_instance_id_redacted": "a2a8ae...9bb4",
        "readonly_verify_running_result": "running",
        "termination_request_sent": True,
        "termination_response_received": True,
        "termination_response_http_status": 200,
        "termination_response_content_type": "application/json",
        "termination_response_body_size_bytes": 652,
        "termination_response_classification": "success_json",
        "readonly_verify_terminated_result": "terminated",
        "termination_verified": True,
        "manual_review_required": False,
        "mutating_operations": 2,
        "billable_action_performed": True,
        "estimated_spend": 0.08134321959353984,
        "elapsed_seconds": 241.0,
        "max_budget": 50.0,
        "max_runtime_minutes": 30,
        "selected_shape": "gpu_1x_a10",
        "selected_candidate": "gpu_1x_a10",
        "selected_candidate_source": "fresh_live_read_only_instance_types",
        "selected_region": "us-east-1",
        "selected_ssh_key_hash": "sha256:e8bd9b2e6fc17b09",
        "metadata_collected": metadata_collected,
        "ssh_attempted": True,
        "host_discovery_attempted": True,
        "host_discovery_status": "FOUND",
        "host_discovery_source": "data[0].ip",
        "host_discovery_source_path": "data[0].ip",
        "host_discovery_poll_count": 40,
        "host_discovery_duration_seconds": 106.334389,
        "ssh_host_present": True,
        "ssh_key_present": True,
        "ssh_auth_result": "remote_command_succeeded",
        "ssh_port_readiness_attempted": True,
        "ssh_port_reachable": True,
        "ssh_port_poll_count": 12,
        "ssh_port_wait_seconds": 45.0,
        "ssh_port_connect_timeout_seconds": 3.0,
        "ssh_exit_status": 0,
        "ssh_redacted_stderr_present": True,
        "ssh_stderr_sha256_prefix": "90744a97872d2c27",
        "ssh_stderr_truncated": False,
        "ssh_stderr_secret_scan_passed": True,
        "remote_command_attempted": True,
        "remote_command": remote_command,
        "remote_command_result": "succeeded",
        "command_output_collected": True,
        "stdout_capture_active": True,
        "stdout_redacted_present": True,
        "stdout_sha256_prefix": "af542830259dac01",
        "stdout_truncated": False,
        "stdout_secret_scan_passed": True,
        "file_transfer_attempted": False,
        "port_forwarding_attempted": False,
        "package_install_attempted": False,
        "training_attempted": training_attempted,
        "old_path_fallback_blocked": True,
        "m039_path_fallback_blocked": True,
        "launch_ready": False,
        "launch_allowed": False,
        "warnings": [],
        "errors": [],
    }
    (workdir / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (workdir / "journal.jsonl").write_text('{"event":"fixture"}\n', encoding="utf-8")
    (workdir / "ledger.json").write_text(
        json.dumps(
            {
                "run_id": "lambda-m063-gpu-visibility-query",
                "owned_instance_id": "redacted-fixture",
                "termination_verified": True,
                "manual_review_required": False,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    write_lambda_m029_spend_audit(
        workdir / "spend-audit.json",
        build_m029_spend_audit(
            estimated_hourly_cost=7.38,
            elapsed_seconds=241.0,
            launch_request_sent=True,
            terminate_request_sent=True,
            termination_verified=True,
            billable_action_performed=True,
        ),
    )
    evidence = {
        "report_schema_version": 1,
        "approved_command": remote_command,
        "command_output_collected": True,
        "stdout_capture_active": True,
        "stdout_redacted": "<redacted-gpu-visibility>",
        "stdout_sha256_prefix": "af542830259dac01",
        "stdout_stored": False,
        "remote_command_attempted": True,
        "remote_command_result": "succeeded",
        "file_transfer_attempted": False,
        "port_forwarding_attempted": False,
        "package_install_attempted": False,
        "training_attempted": training_attempted,
        "launch_ready": False,
        "launch_allowed": False,
    }
    if parsed_fields:
        evidence["parsed_gpu_fields"] = {
            "gpu_name": "NVIDIA A10",
            "memory_total": "23028 MiB",
            "driver_version": "550.54.15",
        }
    (workdir / "ssh-connectivity-evidence.json").write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (workdir / "ssh-host-discovery.json").write_text(
        json.dumps({"status": "FOUND", "source_path": "data[0].ip"}, indent=2) + "\n",
        encoding="utf-8",
    )
    (workdir / "transport-diagnostics.json").write_text(
        json.dumps({"secret_scan": "clean"}, indent=2) + "\n",
        encoding="utf-8",
    )
    instances = []
    unmanaged = []
    if final_instance_count:
        instances = [
            {
                "id": "i-fixture",
                "instance_id": "i-fixture",
                "name": "fixture",
                "status": "running",
            }
        ]
        unmanaged = ["i-fixture"]
    post_discovery = tmp_path / "post-m063-discovery.json"
    write_lambda_live_discovery_report(
        post_discovery,
        LambdaLiveDiscoveryReport(
            live_api_used=True,
            instances=instances,
            unmanaged_instances=unmanaged,
            secret_redacted=True,
            billable_action_performed=False,
            launch_ready=False,
            launch_allowed=False,
        ),
    )
    return {"workdir": workdir, "post_discovery": post_discovery}


def write_m064_chain(tmp_path: Path, **kwargs) -> dict[str, Path]:
    paths = write_m063_gpu_visibility_workdir(tmp_path, **kwargs)
    success_path = tmp_path / "gpu-visibility-success-record.json"
    success = build_lambda_gpu_visibility_success_record_from_paths(
        workdir=paths["workdir"],
        final_discovery=paths["post_discovery"],
    )
    write_lambda_gpu_visibility_success_record(success_path, success)
    output_policy_path = tmp_path / "gpu-visibility-output-policy.json"
    output_policy = build_lambda_gpu_visibility_output_policy()
    write_lambda_gpu_visibility_output_policy(output_policy_path, output_policy)
    parsed_audit_path = tmp_path / "gpu-visibility-parsed-output-audit.json"
    parsed_audit = build_lambda_gpu_visibility_parsed_output_audit_from_paths(
        success_record=success_path,
        output_policy=output_policy_path,
    )
    write_lambda_gpu_visibility_parsed_output_audit(parsed_audit_path, parsed_audit)
    reconciliation_path = tmp_path / "gpu-visibility-reconciliation.json"
    reconciliation = build_lambda_gpu_visibility_reconciliation_from_paths(
        workdir=paths["workdir"],
        success_record=success_path,
        final_discovery=paths["post_discovery"],
    )
    write_lambda_gpu_visibility_reconciliation(reconciliation_path, reconciliation)
    evidence_path = tmp_path / "gpu-visibility-evidence-package.json"
    evidence = build_lambda_gpu_visibility_evidence_package_from_paths(
        success_record=success_path,
        reconciliation=reconciliation_path,
        parsed_output_audit=parsed_audit_path,
    )
    write_lambda_gpu_visibility_evidence_package(evidence_path, evidence)
    closeout_path = tmp_path / "gpu-visibility-closeout.json"
    closeout = build_lambda_gpu_visibility_closeout_from_paths(
        success_record=success_path,
        reconciliation=reconciliation_path,
        evidence_package=evidence_path,
        parsed_output_audit=parsed_audit_path,
    )
    write_lambda_gpu_visibility_closeout(closeout_path, closeout)
    command_policy_path = tmp_path / "python-runtime-command-policy.json"
    command_policy = build_lambda_python_runtime_command_policy()
    write_lambda_python_runtime_command_policy(command_policy_path, command_policy)
    python_output_policy_path = tmp_path / "python-runtime-output-policy.json"
    python_output_policy = build_lambda_python_runtime_output_policy()
    write_lambda_python_runtime_output_policy(
        python_output_policy_path,
        python_output_policy,
    )
    command_review_path = tmp_path / "python-runtime-command-review.json"
    command_review = build_lambda_python_runtime_command_review_from_paths(
        command_policy=command_policy_path,
        output_policy=python_output_policy_path,
    )
    write_lambda_python_runtime_command_review(command_review_path, command_review)
    authorization_path = tmp_path / "m065-python-runtime-authorization.json"
    authorization = build_lambda_m065_python_runtime_authorization_from_paths(
        gpu_visibility_closeout=closeout_path,
        command_policy=command_policy_path,
        output_policy=python_output_policy_path,
        command_review=command_review_path,
    )
    write_lambda_m065_python_runtime_authorization(authorization_path, authorization)
    runbook_path = tmp_path / "m065-python-runtime-runbook-preview.json"
    runbook = build_lambda_m065_python_runtime_runbook_preview_from_path(
        authorization=authorization_path,
    )
    write_lambda_m065_python_runtime_runbook_preview(runbook_path, runbook)
    report_path = tmp_path / "m064-report.json"
    report = build_lambda_m064_report_from_paths(
        success_record=success_path,
        parsed_output_audit=parsed_audit_path,
        reconciliation=reconciliation_path,
        closeout=closeout_path,
        python_command_policy=command_policy_path,
        python_output_policy=python_output_policy_path,
        python_command_review=command_review_path,
        authorization=authorization_path,
        runbook_preview=runbook_path,
    )
    report_path.write_text(report.to_json(), encoding="utf-8")
    return {
        **paths,
        "success": success_path,
        "gpu_output_policy": output_policy_path,
        "parsed_audit": parsed_audit_path,
        "reconciliation": reconciliation_path,
        "evidence": evidence_path,
        "closeout": closeout_path,
        "python_command_policy": command_policy_path,
        "python_output_policy": python_output_policy_path,
        "python_command_review": command_review_path,
        "authorization": authorization_path,
        "runbook": runbook_path,
        "m064_report": report_path,
    }
