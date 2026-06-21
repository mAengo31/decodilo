from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from lambda_m051_helpers import write_m051_inputs
from lambda_m054a_helpers import write_m054a_inputs

from decodilo.lambda_cloud.real_launch_arming import (
    CONFIRM_BILLABLE_ACTION,
    CONFIRM_TERMINATE_REQUIRED,
)
from decodilo.lambda_cloud.ssh_connectivity_m054b_plan import (
    build_lambda_ssh_connectivity_m054b_plan_from_paths,
    write_lambda_ssh_connectivity_m054b_plan,
)


def _write_m054b_plan(tmp_path: Path, monkeypatch) -> dict[str, Path]:
    fake_home = tmp_path / "home"
    fake_ssh = fake_home / ".ssh"
    fake_ssh.mkdir(parents=True)
    (fake_ssh / "existing-key").write_text("fixture-private-key-reference\n")
    monkeypatch.setenv("HOME", str(fake_home))

    m051 = write_m051_inputs(tmp_path / "m051")
    m054a = write_m054a_inputs(tmp_path / "m054a")
    plan_path = tmp_path / "m054b-plan.json"
    plan = build_lambda_ssh_connectivity_m054b_plan_from_paths(
        discovery_report=m051["discovery_m051"],
        execution_plan=m054a["execution_plan"],
        private_key_policy=m054a["private_key_policy"],
        static_validation=m054a["static_validation"],
        price_snapshot=m051["price_snapshot"],
        ssh_key_selection=m051["ssh_key_selection"],
        preferred_metadata_plan=m051["metadata_plan"],
    )
    write_lambda_ssh_connectivity_m054b_plan(plan_path, plan)
    return {
        **m051,
        **{f"m054a_{name}": value for name, value in m054a.items()},
        "m054b_plan": plan_path,
    }


def test_m054b_plan_passes_with_fresh_live_candidate_and_private_reference(
    tmp_path,
    monkeypatch,
):
    paths = _write_m054b_plan(tmp_path, monkeypatch)
    payload = json.loads(paths["m054b_plan"].read_text())

    assert payload["plan_status"] == "plan_passed"
    assert payload["selected_candidate"] == "gpu_8x_a100_80gb_sxm4"
    assert payload["selected_region"] == "us-midwest-1"
    assert payload["private_key_reference_available_for_probe"] is True
    assert payload["max_launch_attempts"] == 1
    assert payload["max_ssh_connectivity_attempts"] == 1
    assert payload["remote_exec_allowed"] is False
    assert payload["file_transfer_allowed"] is False
    assert payload["port_forwarding_allowed"] is False
    assert payload["package_install_allowed"] is False
    assert payload["training_allowed"] is False
    assert payload["launch_ready"] is False
    assert payload["launch_allowed"] is False


def test_m054b_fake_server_launch_probe_and_terminate_flow(tmp_path, monkeypatch):
    paths = _write_m054b_plan(tmp_path, monkeypatch)
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
        "--ssh-key-selection",
        str(paths["ssh_key_selection"]),
        "--response-loss-controls",
        str(paths["controls"]),
    ]
    env = {**os.environ, "HOME": os.environ["HOME"]}
    result = subprocess.run(
        cmd,
        cwd=Path.cwd(),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    report = json.loads((workdir / "report.json").read_text())
    evidence = json.loads((workdir / "ssh-connectivity-evidence.json").read_text())

    assert report["ssh_connectivity_path_used"] is True
    assert report["selected_candidate"] == "gpu_8x_a100_80gb_sxm4"
    assert report["selected_region"] == "us-midwest-1"
    assert report["launch_request_sent"] is True
    assert report["termination_request_sent"] is True
    assert report["termination_verified"] is True
    assert report["host_discovery_attempted"] is True
    assert report["host_discovery_status"] == "FOUND"
    assert report["ssh_host_present"] is True
    assert report["ssh_attempted"] is True
    assert report["remote_command_attempted"] is False
    assert report["file_transfer_attempted"] is False
    assert report["port_forwarding_attempted"] is False
    assert report["package_install_attempted"] is False
    assert report["training_attempted"] is False
    assert report["launch_ready"] is False
    assert report["launch_allowed"] is False
    assert evidence["probe_passed"] is True
    assert evidence["auth_result"] == "fake_probe_succeeded"
    assert evidence["host_discovery_status"] == "FOUND"
    assert evidence["target_host_redacted"] != "<redacted-host>"
    assert evidence["remote_command_attempted"] is False
    assert evidence["file_transfer_attempted"] is False
    assert evidence["port_forwarding_attempted"] is False
    assert evidence["command_output_collected"] is False
