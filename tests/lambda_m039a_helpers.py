from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

from lambda_m038_helpers import write_m038_inputs

from decodilo.cli import _load_m039_lower_cost_execution_gates
from decodilo.lambda_cloud.real_launch_arming import (
    CONFIRM_BILLABLE_ACTION,
    CONFIRM_TERMINATE_REQUIRED,
)

RAW_TEST_SSH_KEY_NAME = "existing-key"


def lower_cost_flag_pairs(paths: dict[str, Path]) -> list[tuple[str, Path]]:
    return [
        ("--m039-authorization", paths["authorization"]),
        ("--lower-cost-canonical-readiness", paths["readiness"]),
        ("--lower-cost-state-snapshot", paths["snapshot"]),
        ("--lower-cost-budget-lock", paths["budget"]),
        ("--lower-cost-resource-lock", paths["resource_lock"]),
        ("--lower-cost-launch-window-lock", paths["window"]),
        ("--lower-cost-launch-plan", paths["plan"]),
        ("--ssh-key-selection", paths["ssh"]),
        ("--response-loss-controls", paths["controls"]),
        ("--lower-cost-gate-check", paths["gate"]),
        ("--m038a-report", paths["m038a"]),
    ]


def lower_cost_flag_args(
    paths: dict[str, Path],
    *,
    omit: set[str] | None = None,
) -> list[str]:
    omitted = omit or set()
    args: list[str] = []
    for flag, path in lower_cost_flag_pairs(paths):
        if flag in omitted:
            continue
        args.extend([flag, str(path)])
    return args


def run_m039_fake(
    tmp_path: Path,
    *,
    omit: set[str] | None = None,
    include_legacy_args: bool = False,
) -> subprocess.CompletedProcess[str]:
    paths = write_m038_inputs(tmp_path / "artifacts", approval_complete=True)
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
        *lower_cost_flag_args(paths, omit=omit),
    ]
    if include_legacy_args:
        cmd.extend(["--m028-report", str(paths["readiness"])])
        cmd.extend(["--m029-authorization", str(paths["authorization"])])
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


def load_lower_cost_gates(paths: dict[str, Path]) -> dict:
    args = SimpleNamespace(
        m039_authorization=paths["authorization"],
        lower_cost_canonical_readiness=paths["readiness"],
        lower_cost_state_snapshot=paths["snapshot"],
        lower_cost_budget_lock=paths["budget"],
        lower_cost_resource_lock=paths["resource_lock"],
        lower_cost_launch_window_lock=paths["window"],
        lower_cost_launch_plan=paths["plan"],
        ssh_key_selection=paths["ssh"],
        response_loss_controls=paths["controls"],
        lower_cost_gate_check=paths["gate"],
        m038a_report=paths["m038a"],
    )
    gates = _load_m039_lower_cost_execution_gates(args)
    assert gates is not None
    return gates
