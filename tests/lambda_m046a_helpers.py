from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

from lambda_m037r_helpers import ssh_selection
from lambda_m045_helpers import write_m045_inputs

from decodilo.cli import _load_m046_capacity_selected_execution_gates
from decodilo.lambda_cloud.capacity_selected_execution_gate_check import (
    build_lambda_capacity_selected_execution_gate_check_from_paths,
    write_lambda_capacity_selected_execution_gate_check,
)
from decodilo.lambda_cloud.m046a_report import (
    build_lambda_m046a_report_from_paths,
    write_lambda_m046a_report,
)
from decodilo.lambda_cloud.real_launch_arming import (
    CONFIRM_BILLABLE_ACTION,
    CONFIRM_TERMINATE_REQUIRED,
)
from decodilo.lambda_cloud.strand_ssh_key_selection import (
    write_lambda_existing_ssh_key_selection,
)

RAW_TEST_SSH_KEY_NAME = "existing-key"


def write_m046a_inputs(
    tmp_path: Path,
    *,
    missing_raw_key: bool = False,
) -> dict[str, Path]:
    paths = write_m045_inputs(tmp_path)
    paths.update(
        {
            "execution_gate_m046": tmp_path / "capacity-selected-execution-gate.json",
            "m046a": tmp_path / "m046a-report.json",
        }
    )
    if missing_raw_key:
        missing = ssh_selection().model_copy(
            update={"selected_ssh_key_name_for_payload": None}
        )
        write_lambda_existing_ssh_key_selection(paths["ssh"], missing)
    execution_gate = build_lambda_capacity_selected_execution_gate_check_from_paths(
        m046_authorization=paths["authorization_m046"],
        cost_risk_review=paths["cost_m045"],
        operator_approval=paths["approval_m045"],
        capacity_selected_gate_check=paths["gate_m045"],
        capacity_aware_selector_output=paths["selector_m044h"],
        capacity_aware_selector_authorization=paths["authorization_m044h"],
        capacity_aware_selector_gate_check=paths["gate_m044h"],
        ssh_key_selection=paths["ssh"],
        response_loss_controls=paths["controls"],
    )
    write_lambda_capacity_selected_execution_gate_check(
        paths["execution_gate_m046"],
        execution_gate,
    )
    report = build_lambda_m046a_report_from_paths(
        execution_gate_check=paths["execution_gate_m046"],
        command_preview=paths["preview_m046"],
    )
    write_lambda_m046a_report(paths["m046a"], report)
    return paths


def capacity_selected_flag_pairs(paths: dict[str, Path]) -> list[tuple[str, Path]]:
    return [
        ("--capacity-selected-m046-authorization", paths["authorization_m046"]),
        ("--capacity-selected-cost-risk-review", paths["cost_m045"]),
        ("--capacity-selected-operator-approval", paths["approval_m045"]),
        ("--capacity-selected-gate-check", paths["gate_m045"]),
        ("--capacity-aware-selector-output", paths["selector_m044h"]),
        ("--capacity-aware-selector-authorization", paths["authorization_m044h"]),
        ("--capacity-aware-selector-gate-check", paths["gate_m044h"]),
        ("--capacity-history", paths["history"]),
        ("--capacity-retry-policy", paths["retry"]),
        ("--ssh-key-selection", paths["ssh"]),
        ("--response-loss-controls", paths["controls"]),
        ("--m045-report", paths["m045"]),
    ]


def capacity_selected_flag_args(
    paths: dict[str, Path],
    *,
    omit: set[str] | None = None,
) -> list[str]:
    omitted = omit or set()
    args: list[str] = []
    for flag, path in capacity_selected_flag_pairs(paths):
        if flag in omitted:
            continue
        args.extend([flag, str(path)])
    return args


def run_m046_fake(
    tmp_path: Path,
    *,
    omit: set[str] | None = None,
    include_legacy_args: bool = False,
    include_m039_args: bool = False,
    missing_raw_key: bool = False,
) -> subprocess.CompletedProcess[str]:
    paths = write_m046a_inputs(tmp_path / "artifacts", missing_raw_key=missing_raw_key)
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
        *capacity_selected_flag_args(paths, omit=omit),
    ]
    if include_legacy_args:
        cmd.extend(["--m028-report", str(paths["m045"])])
        cmd.extend(["--m029-authorization", str(paths["authorization_m046"])])
    if include_m039_args:
        cmd.extend(["--m039-authorization", str(paths["authorization_m046"])])
    result = subprocess.run(
        cmd,
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=False,
    )
    result.paths = paths  # type: ignore[attr-defined]
    result.workdir = workdir  # type: ignore[attr-defined]
    return result


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_capacity_selected_gates(paths: dict[str, Path]) -> dict:
    args = SimpleNamespace(
        capacity_selected_m046_authorization=paths["authorization_m046"],
        capacity_selected_cost_risk_review=paths["cost_m045"],
        capacity_selected_operator_approval=paths["approval_m045"],
        capacity_selected_gate_check=paths["gate_m045"],
        capacity_aware_selector_output=paths["selector_m044h"],
        capacity_aware_selector_authorization=paths["authorization_m044h"],
        capacity_aware_selector_gate_check=paths["gate_m044h"],
        capacity_history=paths["history"],
        capacity_retry_policy=paths["retry"],
        ssh_key_selection=paths["ssh"],
        response_loss_controls=paths["controls"],
        m045_report=paths["m045"],
    )
    gates = _load_m046_capacity_selected_execution_gates(args)
    assert gates is not None
    return gates
