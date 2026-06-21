from __future__ import annotations

import json

from decodilo.lambda_cloud.m054b_closeout import build_lambda_m054b_closeout
from decodilo.lambda_cloud.m055_report import build_lambda_m055_report
from decodilo.lambda_cloud.ssh_connectivity_probe import run_lambda_ssh_connectivity_probe
from decodilo.lambda_cloud.ssh_host_discovery import (
    extract_ssh_host_from_instance_metadata,
    poll_ssh_host_from_provider_metadata,
)
from decodilo.lambda_cloud.ssh_safe_client_command_builder import (
    LambdaSSHSafeClientCommand,
    write_lambda_ssh_safe_client_command,
)


def test_extract_host_from_flat_public_ip():
    result = extract_ssh_host_from_instance_metadata({"public_ip": "8.8.8.8"})

    assert result.status == "FOUND"
    assert result.host == "8.8.8.8"
    assert result.source_path == "public_ip"
    assert result.launch_ready is False
    assert result.launch_allowed is False


def test_extract_host_from_ip_address_and_hostname():
    assert (
        extract_ssh_host_from_instance_metadata({"ip_address": "lambda.example.com"}).host
        == "lambda.example.com"
    )
    assert (
        extract_ssh_host_from_instance_metadata({"hostname": "gpu.lambda.example.com"}).host
        == "gpu.lambda.example.com"
    )


def test_extract_host_from_nested_network_shapes():
    assert (
        extract_ssh_host_from_instance_metadata(
            {"network": {"public_ip": "ssh.lambda.example.com"}}
        ).source_path
        == "network.public_ip"
    )
    assert (
        extract_ssh_host_from_instance_metadata(
            {"network_interfaces": [{"public_ip": "iface.lambda.example.com"}]}
        ).source_path
        == "network_interfaces[0].public_ip"
    )
    assert (
        extract_ssh_host_from_instance_metadata(
            {"network": {"interfaces": [{"public_ip": "nested.lambda.example.com"}]}}
        ).source_path
        == "network.interfaces[0].public_ip"
    )


def test_missing_private_invalid_and_ambiguous_hosts_are_not_silent_successes():
    missing = extract_ssh_host_from_instance_metadata({"status": "running"})
    private = extract_ssh_host_from_instance_metadata({"private_ip": "10.0.0.4"})
    invalid = extract_ssh_host_from_instance_metadata({"public_ip": "not a host"})
    ambiguous = extract_ssh_host_from_instance_metadata(
        {"public_ip": "one.lambda.example.com", "hostname": "two.lambda.example.com"}
    )

    assert missing.status == "NOT_FOUND"
    assert private.status == "NOT_FOUND"
    assert private.rejected_candidates[0]["reason"] == "private_or_non_global_ip_rejected"
    assert invalid.status == "NOT_FOUND"
    assert invalid.rejected_candidates[0]["reason"] == "invalid_hostname"
    assert ambiguous.status == "AMBIGUOUS"
    assert ambiguous.host is None


def test_manual_override_is_explicit_and_validated():
    result = extract_ssh_host_from_instance_metadata(
        {},
        host_override="override.lambda.example.com",
    )
    invalid = extract_ssh_host_from_instance_metadata({}, host_override="https://example.com")

    assert result.status == "FOUND"
    assert result.source_path == "operator_override"
    assert result.override_used is True
    assert invalid.status == "INVALID"
    assert "operator_override_invalid" in invalid.reason_codes


def test_polling_records_key_summaries_and_stops_when_host_appears():
    payloads = [
        [("list_instances", {"data": [{"id": "i-1", "status": "running"}]})],
        [
            (
                "get_instance",
                {"data": {"id": "i-1", "network": {"public_ip": "poll.lambda.example.com"}}},
            )
        ],
    ]

    def fetch():
        return payloads.pop(0)

    result = poll_ssh_host_from_provider_metadata(
        metadata_fetcher=fetch,
        timeout_seconds=10,
        interval_seconds=0,
        max_polls=2,
        sleep_func=lambda _: None,
    )

    assert result.status == "FOUND"
    assert result.poll_count == 2
    assert result.source_path == "data.network.public_ip"
    assert "network" in result.sanitized_metadata_keys


def test_missing_ssh_key_is_not_reported_as_host_discovery_failure(tmp_path):
    safe = LambdaSSHSafeClientCommand(
        command_status="safe_preview",
        command_preview=[
            "ssh",
            "-o",
            "BatchMode=yes",
            "-o",
            "RequestTTY=no",
            "-o",
            "ClearAllForwardings=yes",
            "-o",
            "ForwardAgent=no",
            "-o",
            "ForwardX11=no",
            "-o",
            "PermitLocalCommand=no",
            "-o",
            "ControlMaster=no",
            "-o",
            "SessionType=none",
            "-o",
            "PasswordAuthentication=no",
            "-o",
            "NumberOfPasswordPrompts=0",
            "-o",
            "ConnectTimeout=10",
            "-o",
            "ServerAliveInterval=5",
            "-o",
            "ServerAliveCountMax=1",
            "-N",
            "-T",
            "-i",
            "<redacted-private-key-reference>",
            "lambda-user@<redacted-host>",
        ],
        command_preview_redacted="ssh -N -T <redacted>",
        handshake_only_guaranteed=True,
    )
    safe_path = tmp_path / "safe.json"
    write_lambda_ssh_safe_client_command(safe_path, safe)
    host = extract_ssh_host_from_instance_metadata({"public_ip": "ssh.lambda.example.com"})

    evidence = run_lambda_ssh_connectivity_probe(
        owned_instance_id="i-owned",
        instance_payload={},
        private_key_path=tmp_path / "missing-key",
        safe_client_command=safe_path,
        host_discovery_result=host,
    )

    assert evidence.host_discovery_status == "FOUND"
    assert evidence.auth_result == "ssh_key_missing"
    assert evidence.blockers == ["ssh_key_missing"]


def test_closeout_and_m055_report_keep_m054b_honest():
    closeout = build_lambda_m054b_closeout(
        run_report={
            "launch_request_sent": True,
            "launch_response_received": True,
            "launch_response_http_status": 200,
            "readonly_verify_running_result": "running",
            "termination_request_sent": True,
            "termination_response_received": True,
            "termination_verified": True,
        },
        ssh_evidence={
            "probe_attempted": False,
            "probe_passed": False,
            "blockers": ["ssh_host_not_present_in_provider_metadata"],
        },
        post_discovery={"instances": [], "unmanaged_count": 0},
    )
    report = build_lambda_m055_report(
        closeout=closeout,
        run_report={
            "launch_request_sent": True,
            "launch_response_http_status": 200,
            "termination_request_sent": True,
            "termination_verified": True,
            "host_discovery_status": "NOT_FOUND",
            "ssh_host_present": False,
            "ssh_attempted": False,
            "billable_action_performed": True,
        },
        ssh_evidence={
            "probe_attempted": False,
            "probe_passed": False,
            "auth_result": "host_discovery_failed",
            "blockers": ["ssh_host_not_present_in_provider_metadata"],
        },
        spend_audit={"estimated_spend": 0.22},
        secret_scan_result="clean",
    )

    assert closeout.closeout_status == "lifecycle_successful_ssh_host_discovery_blocked"
    assert closeout.issue_is_host_discovery_not_key_authentication is True
    assert report.manual_review_required is True
    assert report.blocker == "ssh_host_not_present_in_provider_metadata"
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_m055_report_manual_review_false_only_when_everything_clean():
    closeout = build_lambda_m054b_closeout(
        run_report={
            "launch_request_sent": True,
            "launch_response_received": True,
            "launch_response_http_status": 200,
            "readonly_verify_running_result": "running",
            "termination_request_sent": True,
            "termination_response_received": True,
            "termination_verified": True,
        },
        ssh_evidence={"probe_attempted": True, "probe_passed": True},
        post_discovery={"instances": [], "unmanaged_count": 0},
    )
    report = build_lambda_m055_report(
        closeout=closeout,
        run_report={
            "launch_request_sent": True,
            "launch_response_http_status": 200,
            "readonly_verify_running_result": "running",
            "host_discovery_status": "FOUND",
            "ssh_host_present": True,
            "ssh_key_present": True,
            "ssh_attempted": True,
            "ssh_auth_result": "fake_probe_succeeded",
            "remote_command_attempted": False,
            "remote_command_result": "not_attempted",
            "termination_request_sent": True,
            "termination_verified": True,
            "unmanaged_instance_count_post_run": 0,
        },
        ssh_evidence={"probe_attempted": True, "probe_passed": True},
        secret_scan_result="clean",
    )

    assert report.manual_review_required is False
    assert report.report_status == "real_run_success"


def test_host_discovery_public_json_does_not_store_raw_host():
    result = extract_ssh_host_from_instance_metadata({"public_ip": "ssh.lambda.example.com"})
    payload = json.loads(result.to_json(public=True))

    assert payload["host"] is None
    assert payload["host_redacted"] == "ssh...com"
