from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from test_lambda_m056_ssh_retry_execution import _write_m056_inputs
from test_lambda_m059_remote_command_authorization import _authorization_inputs

from decodilo.lambda_cloud.m059_remote_command_authorization import (
    build_lambda_m059_remote_command_authorization_from_paths,
    write_lambda_m059_remote_command_authorization,
)
from decodilo.lambda_cloud.real_launch_arming import (
    CONFIRM_BILLABLE_ACTION,
    CONFIRM_TERMINATE_REQUIRED,
)
from decodilo.lambda_cloud.ssh_identity_command_m059 import (
    build_lambda_m059_identity_command_gate_check_from_paths,
    build_lambda_m059_identity_command_plan_from_paths,
    build_lambda_m059_one_shot_arming_from_paths,
    build_lambda_m059_reviewer_bridge_from_path,
    write_lambda_m059_identity_command_gate_check,
    write_lambda_m059_identity_command_plan,
    write_lambda_m059_one_shot_arming,
    write_lambda_m059_reviewer_bridge,
)


def _write_m059_inputs(tmp_path: Path) -> dict[str, Path]:
    paths = _write_m056_inputs(tmp_path / "m056")
    closeout, stage_policy, command_review = _authorization_inputs(tmp_path / "m059")
    paths.update(
        {
            "m059_stage_policy": stage_policy,
            "m059_command_review": command_review,
            "m059_authorization": tmp_path / "m059-authorization.json",
            "m059_plan": tmp_path / "m059-plan.json",
            "m059_gate": tmp_path / "m059-gate.json",
            "m059_arming": tmp_path / "m059-arming.json",
            "m059_bridge": tmp_path / "m059-bridge.json",
        }
    )
    write_lambda_m059_remote_command_authorization(
        paths["m059_authorization"],
        build_lambda_m059_remote_command_authorization_from_paths(
            ssh_noop_closeout=closeout,
            stage_policy=stage_policy,
            command_review=command_review,
        ),
    )
    write_lambda_m059_identity_command_plan(
        paths["m059_plan"],
        build_lambda_m059_identity_command_plan_from_paths(
            discovery_report=paths["live_discovery"],
            authorization=paths["m059_authorization"],
            stage_policy=stage_policy,
            command_review=command_review,
            ssh_key_selection=paths["ssh_selection"],
            price_snapshot=paths["price_snapshot"],
        ),
    )
    write_lambda_m059_identity_command_gate_check(
        paths["m059_gate"],
        build_lambda_m059_identity_command_gate_check_from_paths(
            plan=paths["m059_plan"],
            authorization=paths["m059_authorization"],
        ),
    )
    write_lambda_m059_one_shot_arming(
        paths["m059_arming"],
        build_lambda_m059_one_shot_arming_from_paths(
            gate_check=paths["m059_gate"],
            response_loss_controls=paths["response_loss_controls"],
            expires_minutes=15,
        ),
    )
    write_lambda_m059_reviewer_bridge(
        paths["m059_bridge"],
        build_lambda_m059_reviewer_bridge_from_path(arming=paths["m059_arming"]),
    )
    return paths


def test_m059_artifact_chain_permits_only_hostname(tmp_path):
    paths = _write_m059_inputs(tmp_path)

    plan = json.loads(paths["m059_plan"].read_text())
    gate = json.loads(paths["m059_gate"].read_text())
    arming = json.loads(paths["m059_arming"].read_text())
    bridge = json.loads(paths["m059_bridge"].read_text())

    assert plan["plan_status"] == "plan_passed"
    assert plan["selected_candidate"] == "gpu_1x_a10"
    assert plan["selected_region"] == "us-east-1"
    assert plan["command_argv"] == ["hostname"]
    assert plan["stdout_capture_allowed"] is True
    assert plan["remote_exec_allowed"] is False
    assert plan["file_transfer_allowed"] is False
    assert plan["port_forwarding_allowed"] is False
    assert plan["package_install_allowed"] is False
    assert plan["training_allowed"] is False
    assert plan["launch_ready"] is False
    assert plan["launch_allowed"] is False
    assert gate["gate_passed"] is True
    assert gate["command"] == "hostname"
    assert gate["max_remote_commands"] == 1
    assert arming["arming_status"] == "armed_for_one_shot_m059_identity_command"
    assert arming["one_shot_request_send_permitted"] is False
    assert bridge["bridge_status"] == "reviewer_compatible_one_shot_ready"
    assert bridge["one_shot_request_send_permitted"] is True
    assert bridge["one_shot_minimal_remote_command_permitted"] is True
    assert bridge["approved_command"] == "hostname"
    assert bridge["launch_ready"] is False
    assert bridge["launch_allowed"] is False


def test_m059_fake_server_flow_runs_hostname_with_redacted_stdout(tmp_path):
    paths = _write_m059_inputs(tmp_path)
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
        "--m059-plan",
        str(paths["m059_plan"]),
        "--m059-gate-check",
        str(paths["m059_gate"]),
        "--m059-authorization",
        str(paths["m059_authorization"]),
        "--m059-one-shot-arming",
        str(paths["m059_arming"]),
        "--m059-reviewer-bridge",
        str(paths["m059_bridge"]),
        "--m056-ssh-static-validation",
        str(paths["m054a_static_validation"]),
        "--m056-ssh-no-exec-audit",
        str(paths["m054a_no_exec_audit"]),
        "--m056-ssh-safe-client-command",
        str(paths["m054a_safe_command"]),
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
    assert report["run_id"] == "lambda-m059-hostname-identity-command"
    assert report["selected_candidate"] == "gpu_1x_a10"
    assert report["selected_region"] == "us-east-1"
    assert report["launch_request_sent"] is True
    assert report["termination_request_sent"] is True
    assert report["termination_verified"] is True
    assert report["ssh_attempted"] is True
    assert report["ssh_auth_result"] == "remote_command_succeeded"
    assert report["remote_command_attempted"] is True
    assert report["remote_command"] == "hostname"
    assert report["remote_command_result"] == "succeeded"
    assert report["command_output_collected"] is True
    assert report["stdout_capture_active"] is True
    assert report["stdout_redacted_present"] is True
    assert report["stdout_secret_scan_passed"] is True
    assert report["file_transfer_attempted"] is False
    assert report["port_forwarding_attempted"] is False
    assert report["package_install_attempted"] is False
    assert report["training_attempted"] is False
    assert evidence["remote_command_attempted"] is True
    assert evidence["approved_command"] == "hostname"
    assert evidence["command_output_collected"] is True
    assert evidence["stdout_capture_active"] is True
    assert evidence["stdout_redacted"] == "<redacted-hostname>"
    assert evidence["stdout_stored"] is False
    assert evidence["stdout_secret_scan_passed"] is True
    assert evidence["file_transfer_attempted"] is False
    assert evidence["port_forwarding_attempted"] is False


def test_m059_requires_all_hostname_artifacts_before_fake_request(tmp_path):
    paths = _write_m059_inputs(tmp_path)
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
        "--m059-plan",
        str(paths["m059_plan"]),
    ]
    result = subprocess.run(
        cmd,
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert "M059 hostname identity-command run requires all M059/SSH artifacts" in (
        result.stderr + result.stdout
    )
    assert not (workdir / "report.json").exists()
