from __future__ import annotations

import json
import shutil
import subprocess

import pytest

from decodilo import cli as decodilo_cli
from decodilo.lambda_cloud import ssh_connectivity_probe as probe_module
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


def _write_safe_ssh_command(path):
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
            "IdentitiesOnly=yes",
            "-o",
            "UserKnownHostsFile=<redacted-run-known-hosts-file>",
            "-o",
            "StrictHostKeyChecking=accept-new",
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
            "ubuntu@<redacted-host>",
        ],
        command_preview_redacted="ssh -N -T <redacted>",
        handshake_only_guaranteed=True,
    )
    write_lambda_ssh_safe_client_command(path, safe)


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
    safe_path = tmp_path / "safe.json"
    _write_safe_ssh_command(safe_path)
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


def test_m055_skips_ssh_when_port_22_never_becomes_reachable(
    tmp_path,
    monkeypatch,
):
    safe_path = tmp_path / "safe.json"
    _write_safe_ssh_command(safe_path)
    key = tmp_path / "lambda-key"
    key.write_text("fixture-private-key-reference\n")
    host = extract_ssh_host_from_instance_metadata({"public_ip": "ssh.lambda.example.com"})

    def fail_if_ssh_runs(*args, **kwargs):  # noqa: ANN001, ANN002
        raise AssertionError("SSH process must not run before port 22 is reachable")

    monkeypatch.setattr(probe_module.subprocess, "run", fail_if_ssh_runs)
    evidence = run_lambda_ssh_connectivity_probe(
        owned_instance_id="i-owned",
        instance_payload={},
        private_key_path=key,
        safe_client_command=safe_path,
        host_discovery_result=host,
        ssh_port_ready_timeout_seconds=0,
        ssh_port_poll_interval_seconds=0,
        tcp_connect_checker=lambda *_: False,
        sleep_func=lambda _: None,
    )

    assert evidence.host_discovery_status == "FOUND"
    assert evidence.ssh_port_readiness_attempted is True
    assert evidence.ssh_port_reachable is False
    assert evidence.ssh_port_poll_count == 1
    assert evidence.probe_attempted is False
    assert evidence.auth_result == "ssh_port_not_reachable"
    assert evidence.blockers == ["ssh_port_not_reachable"]
    assert evidence.remote_command_attempted is False


def test_m055_runs_one_auth_probe_after_port_22_is_reachable(
    tmp_path,
    monkeypatch,
):
    safe_path = tmp_path / "safe.json"
    _write_safe_ssh_command(safe_path)
    key = tmp_path / "lambda-key"
    key.write_text("fixture-private-key-reference\n")
    host = extract_ssh_host_from_instance_metadata({"public_ip": "ssh.lambda.example.com"})
    calls = []

    def fake_ssh_run(command, **kwargs):  # noqa: ANN001
        calls.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(probe_module.subprocess, "run", fake_ssh_run)
    evidence = run_lambda_ssh_connectivity_probe(
        owned_instance_id="i-owned",
        instance_payload={},
        private_key_path=key,
        safe_client_command=safe_path,
        host_discovery_result=host,
        tcp_connect_checker=lambda *_: True,
        sleep_func=lambda _: None,
    )

    assert len(calls) == 1
    assert evidence.ssh_port_readiness_attempted is True
    assert evidence.ssh_port_reachable is True
    assert evidence.ssh_port_poll_count == 1
    assert evidence.probe_attempted is True
    assert evidence.auth_result == "auth_succeeded"
    assert evidence.remote_command_attempted is False


def test_m055_accepts_lambda_ssh_key_as_local_private_key_path(tmp_path, monkeypatch):
    key = tmp_path / "lambda-private-key"
    key.write_text("fixture-private-key-reference\n")
    monkeypatch.delenv("LAMBDA_SSH_PRIVATE_KEY_PATH", raising=False)
    monkeypatch.setenv("LAMBDA_SSH_KEY", str(key))

    assert decodilo_cli._m055_explicit_private_key_path() == key


def test_m055_accepts_lambda_ssh_key_from_env_file_as_ssh_basename(
    tmp_path,
    monkeypatch,
):
    home = tmp_path / "home"
    ssh_dir = home / ".ssh"
    ssh_dir.mkdir(parents=True)
    key = ssh_dir / "lambda-key"
    key.write_text("fixture-private-key-reference\n")
    env_file = tmp_path / ".env"
    env_file.write_text("LAMBDA_SSH_KEY=lambda-key\n")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("LAMBDA_SSH_PRIVATE_KEY_PATH", raising=False)
    monkeypatch.delenv("LAMBDA_SSH_KEY", raising=False)

    assert decodilo_cli._m055_explicit_private_key_path(env_file) == key


def test_m055_accepts_lambda_ssh_key_public_material_from_env_file(
    tmp_path,
    monkeypatch,
):
    home = tmp_path / "home"
    ssh_dir = home / ".ssh"
    ssh_dir.mkdir(parents=True)
    private_key = ssh_dir / "lambda-key"
    public_key = ssh_dir / "lambda-key.pub"
    public_material = (
        "ssh-ed25519 "
        "AAAAC3NzaC1lZDI1NTE5AAAAIFakePublicKeyMaterialForM055TestsOnly "
        "lambda-test-key"
    )
    private_key.write_text("fixture-private-key-reference\n")
    public_key.write_text(public_material + "\n")
    env_file = tmp_path / ".env"
    env_file.write_text(f"LAMBDA_SSH_KEY={public_material}\n")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("LAMBDA_SSH_PRIVATE_KEY_PATH", raising=False)
    monkeypatch.delenv("LAMBDA_SSH_KEY", raising=False)

    assert decodilo_cli._m055_explicit_private_key_path(env_file) == private_key


def test_m055_accepts_lambda_ssh_key_public_comment_from_env_file(
    tmp_path,
    monkeypatch,
):
    home = tmp_path / "home"
    ssh_dir = home / ".ssh"
    ssh_dir.mkdir(parents=True)
    private_key = ssh_dir / "lambda-key"
    public_key = ssh_dir / "lambda-key.pub"
    public_key.write_text(
        "ssh-ed25519 "
        "AAAAC3NzaC1lZDI1NTE5AAAAIFakePublicKeyMaterialForM055TestsOnly "
        "lambda-test-key\n"
    )
    private_key.write_text("fixture-private-key-reference\n")
    env_file = tmp_path / ".env"
    env_file.write_text("LAMBDA_SSH_KEY=lambda-test-key\n")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("LAMBDA_SSH_PRIVATE_KEY_PATH", raising=False)
    monkeypatch.delenv("LAMBDA_SSH_KEY", raising=False)

    assert decodilo_cli._m055_explicit_private_key_path(env_file) == private_key


def test_m055_matches_public_material_to_private_key_without_pub_file(
    tmp_path,
    monkeypatch,
):
    if shutil.which("ssh-keygen") is None:
        pytest.skip("ssh-keygen is unavailable")
    home = tmp_path / "home"
    ssh_dir = home / ".ssh"
    ssh_dir.mkdir(parents=True)
    private_key = ssh_dir / "lambda-key"
    subprocess.run(
        [
            "ssh-keygen",
            "-t",
            "ed25519",
            "-N",
            "",
            "-C",
            "lambda-test-key",
            "-f",
            str(private_key),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    public_material = (ssh_dir / "lambda-key.pub").read_text().strip()
    (ssh_dir / "lambda-key.pub").unlink()
    env_file = tmp_path / ".env"
    env_file.write_text(f"LAMBDA_SSH_KEY={public_material}\n")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("LAMBDA_SSH_PRIVATE_KEY_PATH", raising=False)
    monkeypatch.delenv("LAMBDA_SSH_KEY", raising=False)

    assert decodilo_cli._m055_explicit_private_key_path(env_file) == private_key


def test_m055_reads_billable_confirmation_from_env_file(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("CONFIRM_LAMBDA_BILLABLE_ACTION=true\n")
    monkeypatch.delenv("CONFIRM_LAMBDA_BILLABLE_ACTION", raising=False)

    assert (
        decodilo_cli._m055_env_source_value(
            "CONFIRM_LAMBDA_BILLABLE_ACTION",
            env_file,
        )
        == "true"
    )


def test_m055_private_key_path_takes_precedence_over_lambda_ssh_key(
    tmp_path,
    monkeypatch,
):
    preferred = tmp_path / "preferred-key"
    fallback = tmp_path / "fallback-key"
    preferred.write_text("preferred-private-key-reference\n")
    fallback.write_text("fallback-private-key-reference\n")
    monkeypatch.setenv("LAMBDA_SSH_PRIVATE_KEY_PATH", str(preferred))
    monkeypatch.setenv("LAMBDA_SSH_KEY", str(fallback))

    assert decodilo_cli._m055_explicit_private_key_path() == preferred


def test_m055_rejects_inline_private_key_material_in_lambda_ssh_key(monkeypatch):
    monkeypatch.delenv("LAMBDA_SSH_PRIVATE_KEY_PATH", raising=False)
    monkeypatch.setenv(
        "LAMBDA_SSH_KEY",
        "-----BEGIN " + "OPENSSH PRIVATE KEY" + "-----redacted",
    )

    resolution = decodilo_cli._m055_private_key_resolution()

    assert resolution.path is None
    assert resolution.source == "LAMBDA_SSH_KEY"
    assert resolution.blocker == "LAMBDA_SSH_KEY must name an existing local private key file"


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
