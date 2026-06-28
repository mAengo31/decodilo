from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from lambda_m064_helpers import write_m064_chain
from test_lambda_m061_whoami_identity_command import _write_m061_inputs

from decodilo.lambda_cloud.python_runtime_command_policy import (
    M065_PYTHON_RUNTIME_COMMAND,
)
from decodilo.lambda_cloud.python_runtime_m065_execution import (
    build_lambda_m065_one_shot_arming_from_paths,
    build_lambda_m065_python_runtime_gate_check_from_paths,
    build_lambda_m065_python_runtime_plan_from_paths,
    build_lambda_m065_reviewer_bridge_from_path,
    write_lambda_m065_one_shot_arming,
    write_lambda_m065_python_runtime_gate_check,
    write_lambda_m065_python_runtime_plan,
    write_lambda_m065_reviewer_bridge,
)
from decodilo.lambda_cloud.real_launch_arming import (
    CONFIRM_BILLABLE_ACTION,
    CONFIRM_TERMINATE_REQUIRED,
)


def _write_m065_inputs(tmp_path: Path) -> dict[str, Path]:
    base = _write_m061_inputs(tmp_path / "base")
    m064 = write_m064_chain(tmp_path / "m064", parsed_fields=True)
    paths = {
        **base,
        "m065_authorization": m064["authorization"],
        "m065_command_policy": m064["python_command_policy"],
        "m065_output_policy": m064["python_output_policy"],
        "m065_command_review": m064["python_command_review"],
        "m065_plan": tmp_path / "m065-plan.json",
        "m065_gate": tmp_path / "m065-gate.json",
        "m065_arming": tmp_path / "m065-arming.json",
        "m065_bridge": tmp_path / "m065-bridge.json",
    }
    write_lambda_m065_python_runtime_plan(
        paths["m065_plan"],
        build_lambda_m065_python_runtime_plan_from_paths(
            discovery_report=base["live_discovery"],
            authorization=paths["m065_authorization"],
            command_policy=paths["m065_command_policy"],
            output_policy=paths["m065_output_policy"],
            command_review=paths["m065_command_review"],
            ssh_key_selection=base["ssh_selection"],
            price_snapshot=base["price_snapshot"],
        ),
    )
    write_lambda_m065_python_runtime_gate_check(
        paths["m065_gate"],
        build_lambda_m065_python_runtime_gate_check_from_paths(
            plan=paths["m065_plan"],
            authorization=paths["m065_authorization"],
            command_policy=paths["m065_command_policy"],
            output_policy=paths["m065_output_policy"],
        ),
    )
    write_lambda_m065_one_shot_arming(
        paths["m065_arming"],
        build_lambda_m065_one_shot_arming_from_paths(
            gate_check=paths["m065_gate"],
            response_loss_controls=base["response_loss_controls"],
            expires_minutes=15,
        ),
    )
    write_lambda_m065_reviewer_bridge(
        paths["m065_bridge"],
        build_lambda_m065_reviewer_bridge_from_path(arming=paths["m065_arming"]),
    )
    return paths


def test_m065_artifact_chain_permits_exact_python_version_only(tmp_path):
    paths = _write_m065_inputs(tmp_path)

    plan = json.loads(paths["m065_plan"].read_text())
    gate = json.loads(paths["m065_gate"].read_text())
    arming = json.loads(paths["m065_arming"].read_text())
    bridge = json.loads(paths["m065_bridge"].read_text())

    assert plan["plan_status"] == "plan_passed"
    assert plan["selected_candidate"] == "gpu_1x_a10"
    assert plan["selected_region"] == "us-east-1"
    assert plan["command"] == M065_PYTHON_RUNTIME_COMMAND
    assert plan["command_argv"] == ["python3", "--version"]
    assert plan["python_inline_code_allowed"] is False
    assert plan["python_script_allowed"] is False
    assert plan["python_module_execution_allowed"] is False
    assert plan["python_imports_allowed"] is False
    assert plan["nvidia_smi_allowed"] is False
    assert plan["pip_allowed"] is False
    assert plan["file_transfer_allowed"] is False
    assert plan["port_forwarding_allowed"] is False
    assert plan["package_install_allowed"] is False
    assert plan["training_allowed"] is False
    assert gate["gate_passed"] is True
    assert gate["command"] == M065_PYTHON_RUNTIME_COMMAND
    assert arming["arming_status"] == "armed_for_one_shot_m065_python_runtime_query"
    assert arming["one_shot_request_send_permitted"] is False
    assert bridge["bridge_status"] == "reviewer_compatible_one_shot_ready"
    assert bridge["one_shot_request_send_permitted"] is True
    assert bridge["approved_command"] == M065_PYTHON_RUNTIME_COMMAND
    assert bridge["launch_ready"] is False
    assert bridge["launch_allowed"] is False


def test_m065_fake_server_flow_runs_python_version_with_redacted_stdout(tmp_path):
    paths = _write_m065_inputs(tmp_path)
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
        "--m065-plan",
        str(paths["m065_plan"]),
        "--m065-gate-check",
        str(paths["m065_gate"]),
        "--m065-authorization",
        str(paths["m065_authorization"]),
        "--m065-command-policy",
        str(paths["m065_command_policy"]),
        "--m065-output-policy",
        str(paths["m065_output_policy"]),
        "--m065-command-review",
        str(paths["m065_command_review"]),
        "--m065-one-shot-arming",
        str(paths["m065_arming"]),
        "--m065-reviewer-bridge",
        str(paths["m065_bridge"]),
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
    assert report["run_id"] == "lambda-m065-python-runtime-version-query"
    assert report["selected_candidate"] == "gpu_1x_a10"
    assert report["selected_region"] == "us-east-1"
    assert report["launch_request_sent"] is True
    assert report["termination_request_sent"] is True
    assert report["termination_verified"] is True
    assert report["remote_command_attempted"] is True
    assert report["remote_command"] == M065_PYTHON_RUNTIME_COMMAND
    assert report["remote_command_result"] == "succeeded"
    assert report["command_output_collected"] is True
    assert report["stdout_capture_active"] is True
    assert report["stdout_redacted_present"] is True
    assert report["stdout_secret_scan_passed"] is True
    assert report["file_transfer_attempted"] is False
    assert report["port_forwarding_attempted"] is False
    assert report["package_install_attempted"] is False
    assert report["training_attempted"] is False
    assert evidence["approved_command"] == M065_PYTHON_RUNTIME_COMMAND
    assert evidence["stdout_redacted"] == "<redacted-python-version>"
    assert evidence["stdout_stored"] is False


def test_m065_requires_all_python_runtime_artifacts_before_fake_request(tmp_path):
    paths = _write_m065_inputs(tmp_path)
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
        "--m065-plan",
        str(paths["m065_plan"]),
    ]
    result = subprocess.run(
        cmd,
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert "M065 Python runtime version query run requires all M065/SSH artifacts" in (
        result.stderr + result.stdout
    )
    assert not (workdir / "report.json").exists()
