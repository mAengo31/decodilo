from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from test_lambda_m056_ssh_retry_execution import _write_m056_inputs

from decodilo.lambda_cloud.real_launch_arming import (
    CONFIRM_BILLABLE_ACTION,
    CONFIRM_TERMINATE_REQUIRED,
)
from decodilo.lambda_cloud.ssh_minimal_remote_command_m057 import (
    _real_m057_ssh_command,
    build_lambda_m057_gate_check_from_paths,
    build_lambda_m057_minimal_remote_command_policy,
    build_lambda_m057_one_shot_arming_from_paths,
    build_lambda_m057_operator_approval,
    build_lambda_m057_reviewer_bridge_from_path,
    write_lambda_m057_gate_check,
    write_lambda_m057_minimal_remote_command_policy,
    write_lambda_m057_one_shot_arming,
    write_lambda_m057_operator_approval,
    write_lambda_m057_reviewer_bridge,
)


def _write_m057_inputs(tmp_path: Path) -> dict[str, Path]:
    paths = _write_m056_inputs(tmp_path)
    paths.update(
        {
            "m057_operator_approval": tmp_path / "m057-operator-approval.json",
            "m057_command_policy": tmp_path / "m057-command-policy.json",
            "m057_gate": tmp_path / "m057-gate.json",
            "m057_arming": tmp_path / "m057-arming.json",
            "m057_bridge": tmp_path / "m057-bridge.json",
        }
    )
    write_lambda_m057_operator_approval(
        paths["m057_operator_approval"],
        build_lambda_m057_operator_approval(acknowledge_all=True),
    )
    write_lambda_m057_minimal_remote_command_policy(
        paths["m057_command_policy"],
        build_lambda_m057_minimal_remote_command_policy(),
    )
    write_lambda_m057_gate_check(
        paths["m057_gate"],
        build_lambda_m057_gate_check_from_paths(
            m056_plan=paths["m056_plan"],
            m056_gate_check=paths["m056_gate"],
            operator_approval=paths["m057_operator_approval"],
            command_policy=paths["m057_command_policy"],
            stderr_capture_policy=paths["stderr_policy"],
        ),
    )
    write_lambda_m057_one_shot_arming(
        paths["m057_arming"],
        build_lambda_m057_one_shot_arming_from_paths(
            gate_check=paths["m057_gate"],
            response_loss_controls=paths["response_loss_controls"],
            expires_minutes=15,
        ),
    )
    write_lambda_m057_reviewer_bridge(
        paths["m057_bridge"],
        build_lambda_m057_reviewer_bridge_from_path(arming=paths["m057_arming"]),
    )
    return paths


def test_m057_artifact_chain_permits_only_exact_true(tmp_path):
    paths = _write_m057_inputs(tmp_path)

    approval = json.loads(paths["m057_operator_approval"].read_text())
    policy = json.loads(paths["m057_command_policy"].read_text())
    gate = json.loads(paths["m057_gate"].read_text())
    arming = json.loads(paths["m057_arming"].read_text())
    bridge = json.loads(paths["m057_bridge"].read_text())

    assert approval["approval_status"] == "approved_for_m057_minimal_remote_command"
    assert approval["approved_command"] == "true"
    assert approval["launch_ready"] is False
    assert approval["launch_allowed"] is False
    assert policy["policy_status"] == "policy_defined"
    assert policy["command_argv"] == ["true"]
    assert policy["stdout_collected"] is False
    assert gate["gate_passed"] is True
    assert gate["selected_candidate"] == "gpu_1x_a10"
    assert gate["selected_region"] == "us-east-1"
    assert gate["approved_command"] == "true"
    assert arming["arming_status"] == "armed_for_one_shot_m057_minimal_remote_command"
    assert arming["one_shot_request_send_permitted"] is False
    assert bridge["bridge_status"] == "reviewer_compatible_one_shot_ready"
    assert bridge["one_shot_request_send_permitted"] is True
    assert bridge["one_shot_minimal_remote_command_permitted"] is True
    assert bridge["approved_command"] == "true"
    assert bridge["launch_ready"] is False
    assert bridge["launch_allowed"] is False


def test_m057_fake_server_flow_launches_runs_true_and_terminates(tmp_path):
    paths = _write_m057_inputs(tmp_path)
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
        "--m056-plan",
        str(paths["m056_plan"]),
        "--m056-gate-check",
        str(paths["m056_gate"]),
        "--m056-authorization",
        str(paths["authorization"]),
        "--m056-one-shot-arming",
        str(paths["m056_arming"]),
        "--m056-reviewer-bridge",
        str(paths["m056_bridge"]),
        "--m056-ssh-static-validation",
        str(paths["m054a_static_validation"]),
        "--m056-ssh-no-exec-audit",
        str(paths["m054a_no_exec_audit"]),
        "--m056-ssh-safe-client-command",
        str(paths["m054a_safe_command"]),
        "--m057-operator-approval",
        str(paths["m057_operator_approval"]),
        "--m057-command-policy",
        str(paths["m057_command_policy"]),
        "--m057-gate-check",
        str(paths["m057_gate"]),
        "--m057-one-shot-arming",
        str(paths["m057_arming"]),
        "--m057-reviewer-bridge",
        str(paths["m057_bridge"]),
        "--ssh-stderr-capture-policy",
        str(paths["stderr_policy"]),
        "--ssh-key-selection",
        str(paths["ssh_selection"]),
        "--response-loss-controls",
        str(paths["response_loss_controls"]),
    ]
    result = subprocess.run(
        cmd,
        cwd=Path.cwd(),
        env={**os.environ},
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    report = json.loads((workdir / "report.json").read_text())
    evidence = json.loads((workdir / "ssh-connectivity-evidence.json").read_text())
    assert report["run_id"] == "lambda-m057-minimal-remote-command"
    assert report["selected_candidate"] == "gpu_1x_a10"
    assert report["selected_region"] == "us-east-1"
    assert report["launch_request_sent"] is True
    assert report["termination_request_sent"] is True
    assert report["termination_verified"] is True
    assert report["ssh_attempted"] is True
    assert report["ssh_auth_result"] == "remote_command_succeeded"
    assert report["remote_command_attempted"] is True
    assert report["remote_command_result"] == "succeeded"
    assert report["file_transfer_attempted"] is False
    assert report["port_forwarding_attempted"] is False
    assert report["package_install_attempted"] is False
    assert report["training_attempted"] is False
    assert report["launch_ready"] is False
    assert report["launch_allowed"] is False
    assert evidence["remote_command_attempted"] is True
    assert evidence["approved_command"] == "true"
    assert evidence["command_output_collected"] is False
    assert evidence["stdout_stored"] is False
    assert evidence["file_transfer_attempted"] is False
    assert evidence["port_forwarding_attempted"] is False


def test_m057_requires_m056_artifacts_when_m057_flags_are_present(tmp_path):
    paths = _write_m057_inputs(tmp_path)
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
        "--m057-operator-approval",
        str(paths["m057_operator_approval"]),
        "--m057-command-policy",
        str(paths["m057_command_policy"]),
        "--m057-gate-check",
        str(paths["m057_gate"]),
        "--m057-one-shot-arming",
        str(paths["m057_arming"]),
        "--m057-reviewer-bridge",
        str(paths["m057_bridge"]),
    ]
    result = subprocess.run(
        cmd,
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert "M057 minimal remote-command run requires M056 SSH retry artifacts" in (
        result.stderr + result.stdout
    )
    assert not (workdir / "report.json").exists()


def test_m057_real_ssh_command_executes_only_true_with_safety_flags(tmp_path):
    key = tmp_path / "id_ed25519"
    key.write_text("fixture-private-key-reference\n")

    command = _real_m057_ssh_command(
        host="203.0.113.10",
        private_key_path=key,
        ssh_username="ubuntu",
    )
    joined = " ".join(command)

    assert command[-1] == "true"
    assert "-T" in command
    assert "-N" not in command
    assert "IdentitiesOnly=yes" in command
    assert "StrictHostKeyChecking=accept-new" in command
    assert "UserKnownHostsFile=" in joined
    assert "ClearAllForwardings=yes" in command
    assert "ForwardAgent=no" in command
    assert "ForwardX11=no" in command
    assert "ubuntu@203.0.113.10" in command
    assert "nvidia-smi" not in joined
    assert "python" not in joined
    assert "scp" not in joined
    assert "-L" not in command
    assert "-R" not in command


def test_m057_real_ssh_command_can_be_bound_to_exact_hostname(tmp_path):
    key = tmp_path / "id_ed25519"
    key.write_text("fixture-private-key-reference\n")

    command = _real_m057_ssh_command(
        host="203.0.113.10",
        private_key_path=key,
        ssh_username="ubuntu",
        approved_command="hostname",
    )
    joined = " ".join(command)

    assert command[-1] == "hostname"
    assert "-T" in command
    assert "-N" not in command
    assert "IdentitiesOnly=yes" in command
    assert "ClearAllForwardings=yes" in command
    assert "ubuntu@203.0.113.10" in command
    assert "true" not in command
    assert "whoami" not in joined
    assert "nvidia-smi" not in joined
    assert "python" not in joined
    assert "sh" not in command
    assert "-c" not in command
    assert "-D" not in command


def test_m057_real_ssh_command_can_be_bound_to_exact_whoami(tmp_path):
    key = tmp_path / "id_ed25519"
    key.write_text("fixture-private-key-reference\n")

    command = _real_m057_ssh_command(
        host="203.0.113.10",
        private_key_path=key,
        ssh_username="ubuntu",
        approved_command="whoami",
    )
    joined = " ".join(command)

    assert command[-1] == "whoami"
    assert "-T" in command
    assert "-N" not in command
    assert "IdentitiesOnly=yes" in command
    assert "ClearAllForwardings=yes" in command
    assert "ubuntu@203.0.113.10" in command
    assert "true" not in command
    assert "hostname" not in command
    assert "nvidia-smi" not in joined
    assert "python" not in joined
    assert "sh" not in command
    assert "-c" not in command
    assert "-D" not in command
