from __future__ import annotations

import json
from pathlib import Path

from decodilo.lambda_cloud.live_discovery_report import (
    LambdaLiveDiscoveryReport,
    write_lambda_live_discovery_report,
)
from decodilo.lambda_cloud.real_launch_spend_audit import (
    build_m029_spend_audit,
    write_lambda_m029_spend_audit,
)


def write_m057_noop_workdir(
    tmp_path: Path,
    *,
    command_exit_code: int = 0,
    stdout_stored: bool = False,
    termination_verified: bool = True,
    final_instance_count: int = 0,
    file_transfer_attempted: bool = False,
) -> dict[str, Path]:
    workdir = tmp_path / "m057"
    workdir.mkdir(parents=True)
    report = {
        "report_schema_version": 1,
        "run_id": "lambda-m057-minimal-remote-command",
        "real_lambda_api_used": True,
        "launch_request_sent": True,
        "launch_response_received": True,
        "launch_response_http_status": 200,
        "launch_response_content_type": "application/json",
        "launch_response_body_size_bytes": 63,
        "launch_response_classification": "success_json",
        "owned_instance_id_redacted": "d8f864...61d7",
        "readonly_verify_running_result": "running",
        "termination_request_sent": True,
        "termination_response_received": True,
        "termination_response_http_status": 200,
        "termination_response_content_type": "application/json",
        "termination_response_body_size_bytes": 757,
        "termination_response_classification": "success_json",
        "readonly_verify_terminated_result": "terminating",
        "termination_verified": termination_verified,
        "manual_review_required": not termination_verified,
        "mutating_operations": 2,
        "billable_action_performed": True,
        "estimated_spend": 0.081,
        "elapsed_seconds": 228.0,
        "max_budget": 50.0,
        "max_runtime_minutes": 30,
        "ssh_connectivity_path_used": True,
        "selected_shape": "gpu_1x_a10",
        "selected_candidate": "gpu_1x_a10",
        "selected_candidate_source": "fresh_live_read_only_instance_types",
        "selected_region": "us-east-1",
        "selected_ssh_key_hash": "sha256:e8bd9b2e6fc17b09",
        "strand_payload_compatible": True,
        "ssh_attempted": True,
        "host_discovery_attempted": True,
        "host_discovery_status": "FOUND",
        "host_discovery_source": "data[0].ip",
        "host_discovery_source_path": "data[0].ip",
        "host_discovery_poll_count": 40,
        "host_discovery_duration_seconds": 107.9,
        "ssh_host_present": True,
        "ssh_key_present": True,
        "ssh_auth_result": (
            "remote_command_succeeded" if command_exit_code == 0 else "remote_command_failed"
        ),
        "ssh_port_readiness_attempted": True,
        "ssh_port_reachable": True,
        "ssh_port_poll_count": 16,
        "ssh_port_wait_seconds": 111.3,
        "ssh_port_connect_timeout_seconds": 3.0,
        "ssh_exit_status": command_exit_code,
        "ssh_redacted_stderr_present": True,
        "ssh_stderr_sha256_prefix": "ac19303948991350",
        "ssh_stderr_truncated": False,
        "ssh_stderr_secret_scan_passed": True,
        "remote_command_attempted": True,
        "remote_command_result": "succeeded" if command_exit_code == 0 else "failed",
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
                "run_id": "lambda-m057-minimal-remote-command",
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
            elapsed_seconds=228.0,
            launch_request_sent=True,
            terminate_request_sent=True,
            termination_verified=termination_verified,
            billable_action_performed=True,
        ),
    )
    evidence = {
        "report_schema_version": 1,
        "approved_command": "true",
        "command_output_collected": False,
        "stdout_stored": stdout_stored,
        "remote_command_attempted": True,
        "remote_command_result": "succeeded" if command_exit_code == 0 else "failed",
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
    post_discovery = tmp_path / "post-m057-discovery.json"
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
    secret_scan = tmp_path / "secret-scan.txt"
    secret_scan.write_text("NO_SECRET_PATTERN_MATCHES\n", encoding="utf-8")
    return {
        "workdir": workdir,
        "post_discovery": post_discovery,
        "secret_scan": secret_scan,
    }
