from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from lambda_m054a_helpers import write_m054a_inputs
from lambda_m055d_helpers import write_m055d_base_inputs

from decodilo.lambda_cloud.live_discovery_report import (
    load_lambda_live_discovery_report,
    write_lambda_live_discovery_report,
)
from decodilo.lambda_cloud.read_only_audit import LambdaReadOnlyAuditEntry
from decodilo.lambda_cloud.real_launch_arming import (
    CONFIRM_BILLABLE_ACTION,
    CONFIRM_TERMINATE_REQUIRED,
)
from decodilo.lambda_cloud.ssh_capacity_history import (
    build_lambda_ssh_capacity_history_from_paths,
    write_lambda_ssh_capacity_history,
)
from decodilo.lambda_cloud.ssh_capacity_retry_closeout import (
    build_lambda_ssh_capacity_retry_closeout_from_paths,
    write_lambda_ssh_capacity_retry_closeout,
)
from decodilo.lambda_cloud.ssh_connectivity_m056_gate_check import (
    build_lambda_ssh_connectivity_m056_gate_check_from_paths,
    write_lambda_ssh_connectivity_m056_gate_check,
)
from decodilo.lambda_cloud.ssh_connectivity_m056_one_shot_arming import (
    build_lambda_ssh_connectivity_m056_one_shot_arming_from_paths,
    write_lambda_ssh_connectivity_m056_one_shot_arming,
)
from decodilo.lambda_cloud.ssh_connectivity_m056_plan import (
    build_lambda_ssh_connectivity_m056_plan_from_paths,
    write_lambda_ssh_connectivity_m056_plan,
)
from decodilo.lambda_cloud.ssh_connectivity_m056_reviewer_bridge import (
    build_lambda_ssh_connectivity_m056_reviewer_bridge_from_path,
    write_lambda_ssh_connectivity_m056_reviewer_bridge,
)
from decodilo.lambda_cloud.ssh_connectivity_probe import _real_ssh_command
from decodilo.lambda_cloud.ssh_host_key_policy import (
    build_lambda_ssh_host_key_policy,
    write_lambda_ssh_host_key_policy,
)
from decodilo.lambda_cloud.ssh_identity_policy import (
    build_lambda_ssh_identity_policy,
    write_lambda_ssh_identity_policy,
)
from decodilo.lambda_cloud.ssh_live_candidate_selector import (
    build_lambda_ssh_live_candidate_selection_from_paths,
    write_lambda_ssh_live_candidate_selection,
)
from decodilo.lambda_cloud.ssh_private_key_file_policy import (
    build_lambda_ssh_private_key_file_policy,
    write_lambda_ssh_private_key_file_policy,
)
from decodilo.lambda_cloud.ssh_retry_candidate_policy import (
    build_lambda_ssh_retry_candidate_policy_from_paths,
    write_lambda_ssh_retry_candidate_policy,
)
from decodilo.lambda_cloud.ssh_retry_future_authorization import (
    build_lambda_ssh_retry_future_authorization_from_paths,
    write_lambda_ssh_retry_future_authorization,
)
from decodilo.lambda_cloud.ssh_retry_operator_decision import (
    build_lambda_ssh_retry_operator_decision_from_paths,
    write_lambda_ssh_retry_operator_decision,
)
from decodilo.lambda_cloud.ssh_username_policy import (
    build_lambda_ssh_username_policy,
    write_lambda_ssh_username_policy,
)
from decodilo.lambda_cloud.strand_response_loss_control_check import (
    build_lambda_strand_response_loss_control_check,
    write_lambda_strand_response_loss_control_check,
)


def _write_m056_inputs(tmp_path: Path) -> dict[str, Path]:
    base = write_m055d_base_inputs(tmp_path / "m055d")
    discovery = load_lambda_live_discovery_report(base["live_discovery"])
    write_lambda_live_discovery_report(
        base["live_discovery"],
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
        **base,
        **{f"m054a_{name}": value for name, value in m054a.items()},
        "ssh_closeout": tmp_path / "ssh-closeout.json",
        "capacity_history": tmp_path / "capacity-history.json",
        "candidate_selection": tmp_path / "candidate-selection.json",
        "retry_policy": tmp_path / "retry-policy.json",
        "operator_decision": tmp_path / "operator-decision.json",
        "authorization": tmp_path / "m056-authorization.json",
        "username_policy": tmp_path / "username-policy.json",
        "host_key_policy": tmp_path / "host-key-policy.json",
        "identity_policy": tmp_path / "identity-policy.json",
        "private_key_file_policy": tmp_path / "private-key-file-policy.json",
        "response_loss_controls": tmp_path / "response-loss-controls.json",
        "m056_plan": tmp_path / "m056-plan.json",
        "m056_gate": tmp_path / "m056-gate.json",
        "m056_arming": tmp_path / "m056-arming.json",
        "m056_bridge": tmp_path / "m056-bridge.json",
    }
    write_lambda_ssh_capacity_retry_closeout(
        paths["ssh_closeout"],
        build_lambda_ssh_capacity_retry_closeout_from_paths(
            workdir=paths["workdir"],
            capacity_closeout=paths["capacity_closeout"],
            post_discovery=paths["post_discovery"],
        ),
    )
    write_lambda_ssh_capacity_history(
        paths["capacity_history"],
        build_lambda_ssh_capacity_history_from_paths(
            latest_closeout=paths["ssh_closeout"],
            prior_m055b_report=tmp_path / "missing.json",
        ),
    )
    write_lambda_ssh_live_candidate_selection(
        paths["candidate_selection"],
        build_lambda_ssh_live_candidate_selection_from_paths(
            discovery_report=paths["live_discovery"],
            price_snapshot=paths["price_snapshot"],
            ssh_key_selection=paths["ssh_selection"],
            capacity_history=paths["capacity_history"],
            max_budget=50,
        ),
    )
    write_lambda_ssh_retry_candidate_policy(
        paths["retry_policy"],
        build_lambda_ssh_retry_candidate_policy_from_paths(
            capacity_history=paths["capacity_history"],
            stderr_policy=paths["stderr_policy"],
        ),
    )
    write_lambda_ssh_retry_operator_decision(
        paths["operator_decision"],
        build_lambda_ssh_retry_operator_decision_from_paths(
            candidate_selection=paths["candidate_selection"],
            retry_policy=paths["retry_policy"],
        ),
    )
    write_lambda_ssh_retry_future_authorization(
        paths["authorization"],
        build_lambda_ssh_retry_future_authorization_from_paths(
            capacity_closeout=paths["ssh_closeout"],
            candidate_selection=paths["candidate_selection"],
            retry_policy=paths["retry_policy"],
            operator_decision=paths["operator_decision"],
        ),
    )
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
    write_lambda_strand_response_loss_control_check(
        paths["response_loss_controls"],
        build_lambda_strand_response_loss_control_check(),
    )
    write_lambda_ssh_connectivity_m056_plan(
        paths["m056_plan"],
        build_lambda_ssh_connectivity_m056_plan_from_paths(
            discovery_report=paths["live_discovery"],
            authorization=paths["authorization"],
            username_policy=paths["username_policy"],
            host_key_policy=paths["host_key_policy"],
            identity_policy=paths["identity_policy"],
            private_key_file_policy=paths["private_key_file_policy"],
            stderr_capture_policy=paths["stderr_policy"],
            ssh_key_selection=paths["ssh_selection"],
            price_snapshot=paths["price_snapshot"],
        ),
    )
    write_lambda_ssh_connectivity_m056_gate_check(
        paths["m056_gate"],
        build_lambda_ssh_connectivity_m056_gate_check_from_paths(
            plan=paths["m056_plan"],
            stderr_capture_policy=paths["stderr_policy"],
            retry_policy=paths["retry_policy"],
            safe_client_command=paths["m054a_safe_command"],
            static_validation=paths["m054a_static_validation"],
            no_exec_audit=paths["m054a_no_exec_audit"],
        ),
    )
    write_lambda_ssh_connectivity_m056_one_shot_arming(
        paths["m056_arming"],
        build_lambda_ssh_connectivity_m056_one_shot_arming_from_paths(
            plan=paths["m056_plan"],
            gate_check=paths["m056_gate"],
            authorization=paths["authorization"],
            response_loss_controls=paths["response_loss_controls"],
            expires_minutes=15,
        ),
    )
    write_lambda_ssh_connectivity_m056_reviewer_bridge(
        paths["m056_bridge"],
        build_lambda_ssh_connectivity_m056_reviewer_bridge_from_path(
            arming=paths["m056_arming"],
        ),
    )
    return paths


def test_m056_plan_gate_and_bridge_pass_for_live_a10(tmp_path):
    paths = _write_m056_inputs(tmp_path)

    plan = json.loads(paths["m056_plan"].read_text())
    gate = json.loads(paths["m056_gate"].read_text())
    bridge = json.loads(paths["m056_bridge"].read_text())

    assert plan["plan_status"] == "plan_passed"
    assert plan["selected_candidate"] == "gpu_1x_a10"
    assert plan["selected_region"] == "us-east-1"
    assert plan["launch_ready"] is False
    assert plan["launch_allowed"] is False
    assert gate["gate_passed"] is True
    assert gate["max_launch_attempts"] == 1
    assert gate["max_ssh_attempts"] == 1
    assert bridge["bridge_status"] == "reviewer_compatible_one_shot_ready"
    assert bridge["one_shot_request_send_permitted"] is True


def test_m056_plan_blocks_without_live_a10_in_us_east_1(tmp_path):
    paths = _write_m056_inputs(tmp_path)
    discovery = load_lambda_live_discovery_report(paths["live_discovery"])
    write_lambda_live_discovery_report(
        paths["live_discovery"],
        discovery.model_copy(update={"instance_types": []}),
    )

    report = build_lambda_ssh_connectivity_m056_plan_from_paths(
        discovery_report=paths["live_discovery"],
        authorization=paths["authorization"],
        username_policy=paths["username_policy"],
        host_key_policy=paths["host_key_policy"],
        identity_policy=paths["identity_policy"],
        private_key_file_policy=paths["private_key_file_policy"],
        stderr_capture_policy=paths["stderr_policy"],
        ssh_key_selection=paths["ssh_selection"],
        price_snapshot=paths["price_snapshot"],
    )

    assert report.plan_status == "blocked"
    assert "m056_selected_candidate_not_live_available_in_us_east_1" in report.blockers


def test_m056_fake_server_flow_uses_a10_without_old_shape_fallback(tmp_path):
    paths = _write_m056_inputs(tmp_path)
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
    assert report["selected_candidate"] == "gpu_1x_a10"
    assert report["selected_region"] == "us-east-1"
    assert report["selected_shape"] == "gpu_1x_a10"
    assert report["old_path_fallback_blocked"] is True
    assert report["termination_verified"] is True
    assert report["ssh_attempted"] is True
    assert report["remote_command_attempted"] is False
    assert report["file_transfer_attempted"] is False
    assert report["port_forwarding_attempted"] is False
    assert report["package_install_attempted"] is False
    assert report["training_attempted"] is False


def test_m056_real_ssh_command_uses_isolated_host_key_policy(tmp_path):
    key = tmp_path / "id_ed25519"
    key.write_text("fixture-private-key-reference\n")

    command = _real_ssh_command(
        host="203.0.113.10",
        private_key_path=key,
        ssh_username="ubuntu",
    )
    joined = " ".join(command)

    assert "-N" in command
    assert "-T" in command
    assert "IdentitiesOnly=yes" in command
    assert "StrictHostKeyChecking=accept-new" in command
    assert "UserKnownHostsFile=" in joined
    assert "BatchMode=yes" in command
    assert "ubuntu@203.0.113.10" in command
    assert "nvidia-smi" not in joined
    assert "python" not in joined
    assert "scp" not in joined
