from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from lambda_m037r_helpers import ssh_selection
from lambda_m038_helpers import write_m038_inputs

from decodilo.lambda_cloud.lower_cost_execution_gate_check import (
    build_lambda_lower_cost_execution_gate_check_from_paths,
)
from decodilo.lambda_cloud.strand_ssh_key_selection import (
    write_lambda_existing_ssh_key_selection,
)


def test_lower_cost_execution_gate_check_passes_with_complete_fixture(tmp_path):
    paths = write_m038_inputs(tmp_path, approval_complete=True)

    report = build_lambda_lower_cost_execution_gate_check_from_paths(
        m039_authorization=paths["authorization"],
        canonical_readiness=paths["readiness"],
        state_snapshot=paths["snapshot"],
        budget_lock=paths["budget"],
        resource_lock=paths["resource_lock"],
        launch_window_lock=paths["window"],
        launch_plan=paths["plan"],
        ssh_key_selection=paths["ssh"],
        response_loss_controls=paths["controls"],
    )

    assert report.gate_passed is True
    assert report.raw_ssh_key_available_for_request_construction is True
    assert report.selected_shape == "gpu_1x_h100_pcie"
    assert report.launch_ready is False
    assert report.launch_allowed is False


def test_lower_cost_execution_gate_cli_passes(tmp_path):
    paths = write_m038_inputs(tmp_path, approval_complete=True)
    out = tmp_path / "execution-gate.json"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "lambda",
            "lower-cost",
            "execution-gate-check",
            "--m039-authorization",
            str(paths["authorization"]),
            "--canonical-readiness",
            str(paths["readiness"]),
            "--state-snapshot",
            str(paths["snapshot"]),
            "--budget-lock",
            str(paths["budget"]),
            "--resource-lock",
            str(paths["resource_lock"]),
            "--launch-window-lock",
            str(paths["window"]),
            "--launch-plan",
            str(paths["plan"]),
            "--ssh-key-selection",
            str(paths["ssh"]),
            "--response-loss-controls",
            str(paths["controls"]),
            "--out",
            str(out),
        ],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert '"gate_passed": true' in result.stdout
    assert "existing-key" not in out.read_text(encoding="utf-8")


def test_lower_cost_execution_gate_blocks_missing_raw_key(tmp_path):
    paths = write_m038_inputs(tmp_path, approval_complete=True)
    write_lambda_existing_ssh_key_selection(
        paths["ssh"],
        ssh_selection().model_copy(update={"selected_ssh_key_name_for_payload": None}),
    )

    report = build_lambda_lower_cost_execution_gate_check_from_paths(
        m039_authorization=paths["authorization"],
        canonical_readiness=paths["readiness"],
        state_snapshot=paths["snapshot"],
        budget_lock=paths["budget"],
        resource_lock=paths["resource_lock"],
        launch_window_lock=paths["window"],
        launch_plan=paths["plan"],
        ssh_key_selection=paths["ssh"],
        response_loss_controls=paths["controls"],
    )

    assert report.gate_passed is False
    assert "raw_existing_ssh_key_name_missing_from_private_artifact" in report.blockers
