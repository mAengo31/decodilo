from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from lambda_m037r_helpers import ssh_selection
from lambda_m038_helpers import write_m038_inputs
from lambda_m039a_helpers import (
    RAW_TEST_SSH_KEY_NAME,
    load_json,
    lower_cost_flag_args,
    run_m039_fake,
)

from decodilo.lambda_cloud.real_launch_arming import (
    CONFIRM_BILLABLE_ACTION,
    CONFIRM_TERMINATE_REQUIRED,
)
from decodilo.lambda_cloud.strand_ssh_key_selection import (
    LambdaExistingSSHKeySelectionReport,
    write_lambda_existing_ssh_key_selection,
)


def test_m039_public_reports_redact_private_ssh_key(tmp_path):
    result = run_m039_fake(tmp_path)

    assert result.returncode == 0
    for name in ["report.json", "lower-cost-gates.json", "lower-cost-execution-gate.json"]:
        text = (result.workdir / name).read_text(encoding="utf-8")  # type: ignore[attr-defined]
        assert RAW_TEST_SSH_KEY_NAME not in text
        assert "sha256:" in text
    report = load_json(result.workdir / "report.json")  # type: ignore[attr-defined]
    assert report["selected_ssh_key_hash"].startswith("sha256:")


def test_m039_missing_private_ssh_key_name_blocks(tmp_path):
    paths = write_m038_inputs(tmp_path / "artifacts", approval_complete=True)
    private_missing = ssh_selection().model_copy(
        update={"selected_ssh_key_name_for_payload": None}
    )
    write_lambda_existing_ssh_key_selection(paths["ssh"], private_missing)
    cmd = [
        sys.executable,
        "-m",
        "decodilo.cli",
        "lambda",
        "m029",
        "run",
        "--workdir",
        str(tmp_path / "workdir"),
        "--in-memory-fake",
        "--execute-real-launch",
        "--confirm-billable-action",
        CONFIRM_BILLABLE_ACTION,
        "--confirm-terminate-required",
        CONFIRM_TERMINATE_REQUIRED,
        *lower_cost_flag_args(paths),
    ]
    blocked = subprocess.run(
        cmd,
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=False,
    )

    assert blocked.returncode != 0
    assert "raw_existing_ssh_key_name_missing" in blocked.stderr


def test_m039_raw_public_key_material_rejected():
    with pytest.raises(ValueError, match="raw public key material"):
        LambdaExistingSSHKeySelectionReport.model_validate(
            {
                **ssh_selection().model_dump(mode="json"),
                "raw_public_key_material_present": True,
            }
        )
