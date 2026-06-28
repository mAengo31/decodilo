from __future__ import annotations

import json
import subprocess
import sys


def test_dev_tiny_smoke_cli_writes_bounded_report(tmp_path):
    out = tmp_path / "tiny-smoke.json"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "dev",
            "tiny-smoke",
            "--synthetic",
            "--max-steps",
            "1",
            "--out",
            str(out),
        ],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )

    assert completed.returncode == 0
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["smoke_status"] == "passed"
    assert report["network_used"] is False
    assert report["package_install_attempted"] is False
    assert report["download_attempted"] is False
    assert report["training_attempted"] is False
    assert report["torch_required"] is False
    assert report["gpu_required"] is False
    assert report["launch_ready"] is False
    assert report["launch_allowed"] is False
    assert out.stat().st_size < 8192


def test_dev_tiny_smoke_cli_invalid_steps_exits_nonzero(tmp_path):
    out = tmp_path / "tiny-smoke-failed.json"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "dev",
            "tiny-smoke",
            "--synthetic",
            "--max-steps",
            "2",
            "--out",
            str(out),
        ],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )

    assert completed.returncode != 0
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["smoke_status"] == "failed"
    assert report["network_used"] is False
    assert report["training_attempted"] is False
