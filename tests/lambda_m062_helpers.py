from __future__ import annotations

import json
from pathlib import Path

from decodilo.lambda_cloud.gpu_visibility_command_policy import (
    build_lambda_gpu_visibility_command_policy,
    write_lambda_gpu_visibility_command_policy,
)
from decodilo.lambda_cloud.gpu_visibility_command_review import (
    build_lambda_gpu_visibility_command_review_from_paths,
    write_lambda_gpu_visibility_command_review,
)
from decodilo.lambda_cloud.gpu_visibility_output_policy import (
    build_lambda_gpu_visibility_output_policy,
    write_lambda_gpu_visibility_output_policy,
)
from decodilo.lambda_cloud.live_discovery_report import (
    LambdaLiveDiscoveryReport,
    write_lambda_live_discovery_report,
)
from decodilo.lambda_cloud.m062_report import build_lambda_m062_report_from_paths
from decodilo.lambda_cloud.m063_gpu_visibility_authorization import (
    build_lambda_m063_gpu_visibility_authorization_from_paths,
    write_lambda_m063_gpu_visibility_authorization,
)
from decodilo.lambda_cloud.m063_gpu_visibility_runbook_preview import (
    build_lambda_m063_gpu_visibility_runbook_preview_from_path,
    write_lambda_m063_gpu_visibility_runbook_preview,
)
from decodilo.lambda_cloud.real_launch_spend_audit import (
    build_m029_spend_audit,
    write_lambda_m029_spend_audit,
)
from decodilo.lambda_cloud.whoami_command_closeout import (
    build_lambda_whoami_command_closeout_from_paths,
    write_lambda_whoami_command_closeout,
)
from decodilo.lambda_cloud.whoami_command_evidence_package import (
    build_lambda_whoami_command_evidence_package_from_paths,
    write_lambda_whoami_command_evidence_package,
)
from decodilo.lambda_cloud.whoami_command_reconciliation import (
    build_lambda_whoami_command_reconciliation_from_paths,
    write_lambda_whoami_command_reconciliation,
)
from decodilo.lambda_cloud.whoami_command_success_record import (
    build_lambda_whoami_command_success_record_from_paths,
    write_lambda_whoami_command_success_record,
)


def write_m061_whoami_workdir(
    tmp_path: Path,
    *,
    stdout_stored: bool = False,
    stdout_redacted: str = "<redacted-whoami>",
    termination_verified: bool = True,
    final_instance_count: int = 0,
    file_transfer_attempted: bool = False,
) -> dict[str, Path]:
    workdir = tmp_path / "m061"
    workdir.mkdir(parents=True)
    report = {
        "report_schema_version": 1,
        "run_id": "lambda-m061-whoami-identity-command",
        "real_lambda_api_used": True,
        "launch_request_sent": True,
        "launch_response_received": True,
        "launch_response_http_status": 200,
        "launch_response_content_type": "application/json",
        "launch_response_body_size_bytes": 63,
        "launch_response_classification": "success_json",
        "owned_instance_id_redacted": "de7cc1...979c",
        "readonly_verify_running_result": "running",
        "termination_request_sent": True,
        "termination_response_received": True,
        "termination_response_http_status": 200,
        "termination_response_content_type": "application/json",
        "termination_response_body_size_bytes": 652,
        "termination_response_classification": "success_json",
        "readonly_verify_terminated_result": "terminated",
        "termination_verified": termination_verified,
        "manual_review_required": not termination_verified,
        "mutating_operations": 2,
        "billable_action_performed": True,
        "estimated_spend": 0.07001310201007874,
        "elapsed_seconds": 214.0,
        "max_budget": 50.0,
        "max_runtime_minutes": 30,
        "selected_shape": "gpu_1x_a10",
        "selected_candidate": "gpu_1x_a10",
        "selected_candidate_source": "fresh_live_read_only_instance_types",
        "selected_region": "us-east-1",
        "selected_ssh_key_hash": "sha256:e8bd9b2e6fc17b09",
        "ssh_attempted": True,
        "host_discovery_attempted": True,
        "host_discovery_status": "FOUND",
        "host_discovery_source": "data[0].ip",
        "host_discovery_source_path": "data[0].ip",
        "host_discovery_poll_count": 29,
        "host_discovery_duration_seconds": 84.0,
        "ssh_host_present": True,
        "ssh_key_present": True,
        "ssh_auth_result": "remote_command_succeeded",
        "ssh_port_readiness_attempted": True,
        "ssh_port_reachable": True,
        "ssh_port_poll_count": 14,
        "ssh_port_wait_seconds": 92.0,
        "ssh_port_connect_timeout_seconds": 3.0,
        "ssh_exit_status": 0,
        "ssh_redacted_stderr_present": True,
        "ssh_stderr_sha256_prefix": "90744a97872d2c27",
        "ssh_stderr_truncated": False,
        "ssh_stderr_secret_scan_passed": True,
        "remote_command_attempted": True,
        "remote_command": "whoami",
        "remote_command_result": "succeeded",
        "command_output_collected": True,
        "stdout_capture_active": True,
        "stdout_redacted_present": stdout_redacted == "<redacted-whoami>",
        "stdout_sha256_prefix": "2bd806c97f0e00af",
        "stdout_truncated": False,
        "stdout_secret_scan_passed": True,
        "file_transfer_attempted": file_transfer_attempted,
        "port_forwarding_attempted": False,
        "package_install_attempted": False,
        "training_attempted": False,
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
                "run_id": "lambda-m061-whoami-identity-command",
                "owned_instance_id": "redacted-fixture",
                "termination_verified": termination_verified,
                "manual_review_required": not termination_verified,
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
            estimated_hourly_cost=100.0,
            elapsed_seconds=214.0,
            launch_request_sent=True,
            terminate_request_sent=True,
            termination_verified=termination_verified,
            billable_action_performed=True,
        ),
    )
    evidence = {
        "report_schema_version": 1,
        "approved_command": "whoami",
        "command_output_collected": True,
        "stdout_capture_active": True,
        "stdout_redacted": stdout_redacted,
        "stdout_sha256_prefix": "2bd806c97f0e00af",
        "stdout_stored": stdout_stored,
        "remote_command_attempted": True,
        "remote_command_result": "succeeded",
        "file_transfer_attempted": file_transfer_attempted,
        "port_forwarding_attempted": False,
        "package_install_attempted": False,
        "training_attempted": False,
        "launch_ready": False,
        "launch_allowed": False,
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
    post_discovery = tmp_path / "post-m061-discovery.json"
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


def write_m062_chain(tmp_path: Path, **kwargs) -> dict[str, Path]:
    paths = write_m061_whoami_workdir(tmp_path, **kwargs)
    success_path = tmp_path / "whoami-success.json"
    success = build_lambda_whoami_command_success_record_from_paths(
        workdir=paths["workdir"],
        final_discovery=paths["post_discovery"],
    )
    write_lambda_whoami_command_success_record(success_path, success)
    reconciliation_path = tmp_path / "whoami-reconciliation.json"
    reconciliation = build_lambda_whoami_command_reconciliation_from_paths(
        workdir=paths["workdir"],
        success_record=success_path,
        final_discovery=paths["post_discovery"],
    )
    write_lambda_whoami_command_reconciliation(reconciliation_path, reconciliation)
    evidence_path = tmp_path / "whoami-evidence.json"
    evidence = build_lambda_whoami_command_evidence_package_from_paths(
        success_record=success_path,
        reconciliation=reconciliation_path,
    )
    write_lambda_whoami_command_evidence_package(evidence_path, evidence)
    closeout_path = tmp_path / "whoami-closeout.json"
    closeout = build_lambda_whoami_command_closeout_from_paths(
        success_record=success_path,
        reconciliation=reconciliation_path,
        evidence_package=evidence_path,
    )
    write_lambda_whoami_command_closeout(closeout_path, closeout)
    command_policy_path = tmp_path / "gpu-command-policy.json"
    command_policy = build_lambda_gpu_visibility_command_policy()
    write_lambda_gpu_visibility_command_policy(command_policy_path, command_policy)
    output_policy_path = tmp_path / "gpu-output-policy.json"
    output_policy = build_lambda_gpu_visibility_output_policy()
    write_lambda_gpu_visibility_output_policy(output_policy_path, output_policy)
    command_review_path = tmp_path / "gpu-command-review.json"
    command_review = build_lambda_gpu_visibility_command_review_from_paths(
        command_policy=command_policy_path,
        output_policy=output_policy_path,
    )
    write_lambda_gpu_visibility_command_review(command_review_path, command_review)
    authorization_path = tmp_path / "m063-authorization.json"
    authorization = build_lambda_m063_gpu_visibility_authorization_from_paths(
        whoami_closeout=closeout_path,
        command_policy=command_policy_path,
        output_policy=output_policy_path,
        command_review=command_review_path,
    )
    write_lambda_m063_gpu_visibility_authorization(authorization_path, authorization)
    runbook_path = tmp_path / "m063-runbook.json"
    runbook = build_lambda_m063_gpu_visibility_runbook_preview_from_path(
        authorization=authorization_path,
    )
    write_lambda_m063_gpu_visibility_runbook_preview(runbook_path, runbook)
    report_path = tmp_path / "m062.json"
    report = build_lambda_m062_report_from_paths(
        success_record=success_path,
        reconciliation=reconciliation_path,
        evidence_package=evidence_path,
        closeout=closeout_path,
        command_policy=command_policy_path,
        output_policy=output_policy_path,
        command_review=command_review_path,
        authorization=authorization_path,
        runbook_preview=runbook_path,
    )
    report_path.write_text(report.to_json(), encoding="utf-8")
    return {
        **paths,
        "success": success_path,
        "reconciliation": reconciliation_path,
        "evidence": evidence_path,
        "closeout": closeout_path,
        "command_policy": command_policy_path,
        "output_policy": output_policy_path,
        "command_review": command_review_path,
        "authorization": authorization_path,
        "runbook": runbook_path,
        "m062_report": report_path,
    }
