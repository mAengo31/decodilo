import json
import subprocess
import sys

import pytest
from lambda_fake_lifecycle_helpers import write_approved_m020, write_incomplete_approval

from decodilo.lambda_cloud.fake_lifecycle_preflight import run_fake_lambda_lifecycle_preflight


def test_fake_lifecycle_approval_gate_blocks_incomplete_approval(tmp_path) -> None:
    _report, m020_path, _approval_path = write_approved_m020(tmp_path)
    incomplete = write_incomplete_approval(tmp_path)

    preflight = run_fake_lambda_lifecycle_preflight(
        m020_report=m020_path,
        approval_manifest=incomplete,
    )

    assert preflight.passed is False
    assert "approval acknowledgements are incomplete" in preflight.errors


@pytest.mark.integration
def test_approval_template_can_approve_fake_lifecycle_only(tmp_path) -> None:
    out = tmp_path / "approval.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "lambda",
            "approval-template",
            "--instance-type",
            "gpu_8x_h100_sxm",
            "--region",
            "us-west-1",
            "--gpu-type",
            "H100 SXM",
            "--gpus-per-instance",
            "8",
            "--max-budget",
            "50",
            "--max-runtime-minutes",
            "30",
            "--approve-fake-lifecycle",
            "--out",
            str(out),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    manifest = json.loads(out.read_text(encoding="utf-8"))

    assert payload["approval_status"] == "approved_for_future_fake_launch_lifecycle"
    assert manifest["approval_status"] == "approved_for_future_fake_launch_lifecycle"
    assert manifest["launch_allowed"] is False


@pytest.mark.integration
def test_approval_template_rejects_over_policy_fake_lifecycle(tmp_path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "lambda",
            "approval-template",
            "--instance-type",
            "gpu_8x_h100_sxm",
            "--region",
            "us-west-1",
            "--gpu-type",
            "H100 SXM",
            "--gpus-per-instance",
            "8",
            "--max-budget",
            "51",
            "--approve-fake-lifecycle",
            "--out",
            str(tmp_path / "approval.json"),
        ],
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    assert "exceeds" in completed.stdout
