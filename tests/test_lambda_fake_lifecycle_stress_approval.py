import json
import subprocess
import sys

import pytest

pytestmark = pytest.mark.integration


def test_approval_template_can_include_fake_stress_scope(tmp_path) -> None:
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
            "--approve-fake-lifecycle",
            "--approve-fake-stress",
            "--out",
            str(out),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    manifest = json.loads(out.read_text(encoding="utf-8"))

    assert json.loads(completed.stdout)["approval_status"] == (
        "approved_for_future_fake_launch_lifecycle"
    )
    assert manifest["approval_scope"] == ["approved_for_fake_lifecycle_stress"]
    assert manifest["launch_allowed"] is False


def test_fake_stress_approval_requires_fake_lifecycle_approval(tmp_path) -> None:
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
            "--approve-fake-stress",
            "--out",
            str(tmp_path / "approval.json"),
        ],
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    assert "--approve-fake-stress requires --approve-fake-lifecycle" in completed.stdout
