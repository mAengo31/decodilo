from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from lambda_m051_helpers import write_m051_inputs
from lambda_m054a_helpers import write_m054a_inputs

from decodilo.lambda_cloud.live_discovery_report import (
    load_lambda_live_discovery_report,
    write_lambda_live_discovery_report,
)
from decodilo.lambda_cloud.read_only_audit import LambdaReadOnlyAuditEntry
from decodilo.lambda_cloud.real_launch_arming import (
    CONFIRM_BILLABLE_ACTION,
    CONFIRM_TERMINATE_REQUIRED,
)
from decodilo.lambda_cloud.ssh_connectivity_m054b_plan import (
    build_lambda_ssh_connectivity_m054b_plan_from_paths,
    write_lambda_ssh_connectivity_m054b_plan,
)
from decodilo.lambda_cloud.ssh_connectivity_m055c_gate_check import (
    build_lambda_ssh_connectivity_m055c_gate_check_from_paths,
    write_lambda_ssh_connectivity_m055c_gate_check,
)
from decodilo.lambda_cloud.ssh_connectivity_m055c_plan import (
    build_lambda_ssh_connectivity_m055c_plan_from_paths,
    write_lambda_ssh_connectivity_m055c_plan,
)
from decodilo.lambda_cloud.ssh_connectivity_probe import (
    run_lambda_ssh_connectivity_probe,
)
from decodilo.lambda_cloud.ssh_failure_stderr_capture import (
    build_lambda_ssh_stderr_capture_policy,
    write_lambda_ssh_stderr_capture_policy,
)
from decodilo.lambda_cloud.ssh_host_key_policy import (
    build_lambda_ssh_host_key_policy,
    write_lambda_ssh_host_key_policy,
)
from decodilo.lambda_cloud.ssh_identity_policy import (
    build_lambda_ssh_identity_policy,
    write_lambda_ssh_identity_policy,
)
from decodilo.lambda_cloud.ssh_private_key_file_policy import (
    build_lambda_ssh_private_key_file_policy,
    write_lambda_ssh_private_key_file_policy,
)
from decodilo.lambda_cloud.ssh_safe_client_command_builder import (
    load_lambda_ssh_safe_client_command,
)
from decodilo.lambda_cloud.ssh_username_policy import (
    build_lambda_ssh_username_policy,
    write_lambda_ssh_username_policy,
)


def _write_m055c_inputs(tmp_path: Path, monkeypatch) -> dict[str, Path]:
    fake_home = tmp_path / "home"
    fake_ssh = fake_home / ".ssh"
    fake_ssh.mkdir(parents=True)
    (fake_ssh / "existing-key").write_text("fixture-private-key-reference\n")
    monkeypatch.setenv("HOME", str(fake_home))

    m051 = write_m051_inputs(tmp_path / "m051")
    discovery = load_lambda_live_discovery_report(m051["discovery_m051"])
    write_lambda_live_discovery_report(
        m051["discovery_m051"],
        discovery.model_copy(
            update={
                "audit_log": [
                    LambdaReadOnlyAuditEntry(
                        operation="list_instance_types",
                        method="GET",
                        endpoint="/instance-types",
                        allowed=True,
                        status_code=200,
                        live_api_used=True,
                    )
                ]
            }
        ),
    )
    m054a = write_m054a_inputs(tmp_path / "m054a")
    paths = {
        **m051,
        **{f"m054a_{name}": value for name, value in m054a.items()},
        "m054b_plan": tmp_path / "m054b-plan.json",
        "username_policy": tmp_path / "username-policy.json",
        "host_key_policy": tmp_path / "host-key-policy.json",
        "identity_policy": tmp_path / "identity-policy.json",
        "private_key_file_policy": tmp_path / "private-key-file-policy.json",
        "stderr_policy": tmp_path / "stderr-policy.json",
        "m055c_plan": tmp_path / "m055c-plan.json",
        "m055c_gate": tmp_path / "m055c-gate.json",
    }
    m054b_plan = build_lambda_ssh_connectivity_m054b_plan_from_paths(
        discovery_report=m051["discovery_m051"],
        execution_plan=m054a["execution_plan"],
        private_key_policy=m054a["private_key_policy"],
        static_validation=m054a["static_validation"],
        price_snapshot=m051["price_snapshot"],
        ssh_key_selection=m051["ssh_key_selection"],
        preferred_metadata_plan=m051["metadata_plan"],
    )
    write_lambda_ssh_connectivity_m054b_plan(paths["m054b_plan"], m054b_plan)
    write_lambda_ssh_username_policy(
        paths["username_policy"],
        build_lambda_ssh_username_policy(),
    )
    write_lambda_ssh_host_key_policy(
        paths["host_key_policy"],
        build_lambda_ssh_host_key_policy(),
    )
    write_lambda_ssh_identity_policy(
        paths["identity_policy"],
        build_lambda_ssh_identity_policy(),
    )
    write_lambda_ssh_private_key_file_policy(
        paths["private_key_file_policy"],
        build_lambda_ssh_private_key_file_policy(checked_mode=0o600),
    )
    write_lambda_ssh_stderr_capture_policy(
        paths["stderr_policy"],
        build_lambda_ssh_stderr_capture_policy(),
    )
    m055c_plan = build_lambda_ssh_connectivity_m055c_plan_from_paths(
        discovery_report=m051["discovery_m051"],
        username_policy=paths["username_policy"],
        host_key_policy=paths["host_key_policy"],
        identity_policy=paths["identity_policy"],
        private_key_file_policy=paths["private_key_file_policy"],
        stderr_capture_policy=paths["stderr_policy"],
        ssh_key_selection=m051["ssh_key_selection"],
        price_snapshot=m051["price_snapshot"],
        preferred_metadata_plan=m051["metadata_plan"],
    )
    write_lambda_ssh_connectivity_m055c_plan(paths["m055c_plan"], m055c_plan)
    gate = build_lambda_ssh_connectivity_m055c_gate_check_from_paths(
        plan=paths["m055c_plan"],
        safe_client_command=m054a["safe_command"],
        static_validation=m054a["static_validation"],
        no_exec_audit=m054a["no_exec_audit"],
        stderr_capture_policy=paths["stderr_policy"],
    )
    write_lambda_ssh_connectivity_m055c_gate_check(paths["m055c_gate"], gate)
    return paths


def test_m055c_plan_and_gate_pass_with_stderr_capture(tmp_path, monkeypatch):
    paths = _write_m055c_inputs(tmp_path, monkeypatch)
    plan = json.loads(paths["m055c_plan"].read_text())
    gate = json.loads(paths["m055c_gate"].read_text())
    safe = load_lambda_ssh_safe_client_command(paths["m054a_safe_command"])

    assert plan["plan_status"] == "plan_passed"
    assert plan["ssh_username"] == "ubuntu"
    assert plan["stderr_capture_enabled"] is True
    assert plan["launch_ready"] is False
    assert plan["launch_allowed"] is False
    assert gate["gate_passed"] is True
    assert gate["stderr_capture_active"] is True
    assert gate["max_ssh_attempts"] == 1
    assert "-N" in safe.command_preview
    assert "-T" in safe.command_preview


def test_m055c_fake_server_flow_accepts_diagnostic_gate_flags(tmp_path, monkeypatch):
    paths = _write_m055c_inputs(tmp_path, monkeypatch)
    workdir = tmp_path / "workdir"
    cmd = [
        sys.executable,
        "-m",
        "decodilo.cli",
        "lambda",
        "m029",
        "run",
        "--workdir",
        str(workdir),
        "--in-memory-fake",
        "--execute-real-launch",
        "--confirm-billable-action",
        CONFIRM_BILLABLE_ACTION,
        "--confirm-terminate-required",
        CONFIRM_TERMINATE_REQUIRED,
        "--m054b-plan",
        str(paths["m054b_plan"]),
        "--m054-ssh-one-shot-arming",
        str(paths["m054a_one_shot_arming"]),
        "--m054-ssh-reviewer-bridge",
        str(paths["m054a_reviewer_bridge"]),
        "--m054-ssh-static-validation",
        str(paths["m054a_static_validation"]),
        "--m054-ssh-no-exec-audit",
        str(paths["m054a_no_exec_audit"]),
        "--m054-ssh-command-preview",
        str(paths["m054a_command_preview"]),
        "--m054-ssh-safe-client-command",
        str(paths["m054a_safe_command"]),
        "--m055c-plan",
        str(paths["m055c_plan"]),
        "--m055c-gate-check",
        str(paths["m055c_gate"]),
        "--ssh-stderr-capture-policy",
        str(paths["stderr_policy"]),
        "--ssh-key-selection",
        str(paths["ssh_key_selection"]),
        "--response-loss-controls",
        str(paths["controls"]),
    ]
    result = subprocess.run(
        cmd,
        cwd=Path.cwd(),
        env={**os.environ, "HOME": os.environ["HOME"]},
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    report = json.loads((workdir / "report.json").read_text())
    evidence = json.loads((workdir / "ssh-connectivity-evidence.json").read_text())

    assert report["ssh_connectivity_path_used"] is True
    assert report["ssh_attempted"] is True
    assert report["remote_command_attempted"] is False
    assert report["file_transfer_attempted"] is False
    assert report["port_forwarding_attempted"] is False
    assert report["launch_ready"] is False
    assert report["launch_allowed"] is False
    assert evidence["stderr_capture_active"] is True
    assert evidence["auth_result"] == "fake_probe_succeeded"


def test_ssh_failure_probe_persists_redacted_stderr_and_classification(
    tmp_path,
    monkeypatch,
):
    paths = _write_m055c_inputs(tmp_path, monkeypatch)
    key = tmp_path / "private-key"
    key.write_text("fixture-private-key-reference\n")
    key.chmod(0o600)

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=255,
            stderr=(
                f"ubuntu@m055c-test.example.com: Permission denied (publickey). "
                f"Identity file {key} not accessible."
            ),
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    evidence = run_lambda_ssh_connectivity_probe(
        owned_instance_id="instance-1234567890abcdef",
        instance_payload={"hostname": "m055c-test.example.com"},
        private_key_path=key,
        safe_client_command=paths["m054a_safe_command"],
        ssh_username="ubuntu",
        tcp_connect_checker=lambda host, port, timeout: True,
    )

    assert evidence.probe_attempted is True
    assert evidence.probe_passed is False
    assert evidence.exit_status == 255
    assert evidence.ssh_failure_classification == "identity_file_not_found"
    assert evidence.redacted_stderr_present is True
    assert str(key) not in (evidence.stderr_redacted or "")
    assert "m055c-test.example.com" not in (evidence.stderr_redacted or "")
    assert evidence.stderr_secret_scan_passed is True
    assert evidence.remote_command_attempted is False
    assert evidence.file_transfer_attempted is False
    assert evidence.port_forwarding_attempted is False
