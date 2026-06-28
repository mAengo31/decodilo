from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from lambda_m060_helpers import write_m059_hostname_workdir
from test_lambda_m059_hostname_identity_command import _write_m059_inputs

from decodilo.lambda_cloud.m060_report import (
    build_lambda_m060_report_from_paths,
    write_lambda_m060_report,
)
from decodilo.lambda_cloud.m061_next_step_decision import (
    build_lambda_m061_next_step_decision_from_paths,
    write_lambda_m061_next_step_decision,
)
from decodilo.lambda_cloud.m061_whoami_authorization import (
    build_lambda_m061_whoami_authorization_from_paths,
    write_lambda_m061_whoami_authorization,
)
from decodilo.lambda_cloud.real_launch_arming import (
    CONFIRM_BILLABLE_ACTION,
    CONFIRM_TERMINATE_REQUIRED,
)
from decodilo.lambda_cloud.ssh_hostname_identity_closeout import (
    build_lambda_ssh_hostname_identity_closeout_from_paths,
    write_lambda_ssh_hostname_identity_closeout,
)
from decodilo.lambda_cloud.ssh_hostname_identity_evidence_package import (
    build_lambda_ssh_hostname_identity_evidence_package_from_paths,
    write_lambda_ssh_hostname_identity_evidence_package,
)
from decodilo.lambda_cloud.ssh_hostname_identity_reconciliation import (
    build_lambda_ssh_hostname_identity_reconciliation_from_paths,
    write_lambda_ssh_hostname_identity_reconciliation,
)
from decodilo.lambda_cloud.ssh_hostname_identity_success_record import (
    build_lambda_ssh_hostname_identity_success_record_from_paths,
    write_lambda_ssh_hostname_identity_success_record,
)
from decodilo.lambda_cloud.ssh_whoami_identity_command_m061 import (
    build_lambda_m061_identity_command_gate_check_from_paths,
    build_lambda_m061_identity_command_plan_from_paths,
    build_lambda_m061_one_shot_arming_from_paths,
    build_lambda_m061_reviewer_bridge_from_path,
    write_lambda_m061_identity_command_gate_check,
    write_lambda_m061_identity_command_plan,
    write_lambda_m061_one_shot_arming,
    write_lambda_m061_reviewer_bridge,
)


def _write_m061_inputs(tmp_path: Path) -> dict[str, Path]:
    paths = _write_m059_inputs(tmp_path / "m059_inputs")
    hostname = write_m059_hostname_workdir(tmp_path / "m060_inputs")
    paths.update(
        {
            "hostname_success": tmp_path / "hostname-success.json",
            "hostname_reconciliation": tmp_path / "hostname-reconciliation.json",
            "hostname_evidence": tmp_path / "hostname-evidence.json",
            "hostname_closeout": tmp_path / "hostname-closeout.json",
            "m061_decision": tmp_path / "m061-decision.json",
            "m060_report": tmp_path / "m060-report.json",
            "m061_authorization": tmp_path / "m061-authorization.json",
            "m061_plan": tmp_path / "m061-plan.json",
            "m061_gate": tmp_path / "m061-gate.json",
            "m061_arming": tmp_path / "m061-arming.json",
            "m061_bridge": tmp_path / "m061-bridge.json",
        }
    )
    write_lambda_ssh_hostname_identity_success_record(
        paths["hostname_success"],
        build_lambda_ssh_hostname_identity_success_record_from_paths(
            workdir=hostname["workdir"],
            final_discovery=hostname["post_discovery"],
        ),
    )
    write_lambda_ssh_hostname_identity_reconciliation(
        paths["hostname_reconciliation"],
        build_lambda_ssh_hostname_identity_reconciliation_from_paths(
            workdir=hostname["workdir"],
            success_record=paths["hostname_success"],
            final_discovery=hostname["post_discovery"],
        ),
    )
    write_lambda_ssh_hostname_identity_evidence_package(
        paths["hostname_evidence"],
        build_lambda_ssh_hostname_identity_evidence_package_from_paths(
            success_record=paths["hostname_success"],
            reconciliation=paths["hostname_reconciliation"],
        ),
    )
    write_lambda_ssh_hostname_identity_closeout(
        paths["hostname_closeout"],
        build_lambda_ssh_hostname_identity_closeout_from_paths(
            success_record=paths["hostname_success"],
            reconciliation=paths["hostname_reconciliation"],
            evidence_package=paths["hostname_evidence"],
        ),
    )
    write_lambda_m061_next_step_decision(
        paths["m061_decision"],
        build_lambda_m061_next_step_decision_from_paths(
            hostname_closeout=paths["hostname_closeout"],
        ),
    )
    write_lambda_m060_report(
        paths["m060_report"],
        build_lambda_m060_report_from_paths(
            success_record=paths["hostname_success"],
            reconciliation=paths["hostname_reconciliation"],
            evidence_package=paths["hostname_evidence"],
            closeout=paths["hostname_closeout"],
            decision=paths["m061_decision"],
        ),
    )
    write_lambda_m061_whoami_authorization(
        paths["m061_authorization"],
        build_lambda_m061_whoami_authorization_from_paths(
            m060_report=paths["m060_report"],
            hostname_closeout=paths["hostname_closeout"],
            decision=paths["m061_decision"],
        ),
    )
    write_lambda_m061_identity_command_plan(
        paths["m061_plan"],
        build_lambda_m061_identity_command_plan_from_paths(
            discovery_report=paths["live_discovery"],
            authorization=paths["m061_authorization"],
            hostname_closeout=paths["hostname_closeout"],
            ssh_key_selection=paths["ssh_selection"],
            price_snapshot=paths["price_snapshot"],
        ),
    )
    write_lambda_m061_identity_command_gate_check(
        paths["m061_gate"],
        build_lambda_m061_identity_command_gate_check_from_paths(
            plan=paths["m061_plan"],
            authorization=paths["m061_authorization"],
        ),
    )
    write_lambda_m061_one_shot_arming(
        paths["m061_arming"],
        build_lambda_m061_one_shot_arming_from_paths(
            gate_check=paths["m061_gate"],
            response_loss_controls=paths["response_loss_controls"],
            expires_minutes=15,
        ),
    )
    write_lambda_m061_reviewer_bridge(
        paths["m061_bridge"],
        build_lambda_m061_reviewer_bridge_from_path(arming=paths["m061_arming"]),
    )
    return paths


def test_m061_artifact_chain_permits_only_whoami(tmp_path):
    paths = _write_m061_inputs(tmp_path)

    plan = json.loads(paths["m061_plan"].read_text())
    gate = json.loads(paths["m061_gate"].read_text())
    arming = json.loads(paths["m061_arming"].read_text())
    bridge = json.loads(paths["m061_bridge"].read_text())

    assert plan["plan_status"] == "plan_passed"
    assert plan["selected_candidate"] == "gpu_1x_a10"
    assert plan["selected_region"] == "us-east-1"
    assert plan["command_argv"] == ["whoami"]
    assert plan["stdout_capture_allowed"] is True
    assert plan["remote_exec_allowed"] is False
    assert plan["file_transfer_allowed"] is False
    assert plan["port_forwarding_allowed"] is False
    assert plan["package_install_allowed"] is False
    assert plan["training_allowed"] is False
    assert gate["gate_passed"] is True
    assert gate["command"] == "whoami"
    assert arming["arming_status"] == "armed_for_one_shot_m061_identity_command"
    assert arming["one_shot_request_send_permitted"] is False
    assert bridge["bridge_status"] == "reviewer_compatible_one_shot_ready"
    assert bridge["one_shot_request_send_permitted"] is True
    assert bridge["approved_command"] == "whoami"
    assert bridge["launch_ready"] is False
    assert bridge["launch_allowed"] is False


def test_m061_fake_server_flow_runs_whoami_with_redacted_stdout(tmp_path):
    paths = _write_m061_inputs(tmp_path)
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
        "--m061-plan",
        str(paths["m061_plan"]),
        "--m061-gate-check",
        str(paths["m061_gate"]),
        "--m061-authorization",
        str(paths["m061_authorization"]),
        "--m061-one-shot-arming",
        str(paths["m061_arming"]),
        "--m061-reviewer-bridge",
        str(paths["m061_bridge"]),
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
    assert report["run_id"] == "lambda-m061-whoami-identity-command"
    assert report["selected_candidate"] == "gpu_1x_a10"
    assert report["selected_region"] == "us-east-1"
    assert report["launch_request_sent"] is True
    assert report["termination_request_sent"] is True
    assert report["termination_verified"] is True
    assert report["remote_command_attempted"] is True
    assert report["remote_command"] == "whoami"
    assert report["remote_command_result"] == "succeeded"
    assert report["command_output_collected"] is True
    assert report["stdout_capture_active"] is True
    assert report["stdout_redacted_present"] is True
    assert report["stdout_secret_scan_passed"] is True
    assert report["file_transfer_attempted"] is False
    assert report["port_forwarding_attempted"] is False
    assert report["package_install_attempted"] is False
    assert report["training_attempted"] is False
    assert evidence["approved_command"] == "whoami"
    assert evidence["stdout_redacted"] == "<redacted-whoami>"
    assert evidence["stdout_stored"] is False


def test_m061_requires_all_whoami_artifacts_before_fake_request(tmp_path):
    paths = _write_m061_inputs(tmp_path)
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
        "--m061-plan",
        str(paths["m061_plan"]),
    ]
    result = subprocess.run(
        cmd,
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert "M061 whoami identity-command run requires all M061/SSH artifacts" in (
        result.stderr + result.stdout
    )
    assert not (workdir / "report.json").exists()
