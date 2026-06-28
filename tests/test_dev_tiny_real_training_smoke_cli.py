from __future__ import annotations

import json
import subprocess
import sys


def test_tiny_real_training_smoke_cli_passes(tmp_path):
    report_path = tmp_path / "tiny-real-training-smoke.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "dev",
            "tiny-real-training-smoke",
            "--synthetic",
            "--model",
            "tiny-linear",
            "--steps",
            "1",
            "--optimizer",
            "adamw",
            "--out",
            str(report_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["tiny_real_training_smoke_status"] == "passed"
    assert report["command"] == "dev tiny-real-training-smoke"
    assert report["steps_completed"] == 1
    assert report["training_attempted"] is True
    assert report["real_training_mechanics_exercised"] is True
    assert report["loss_finite_check_passed"] is True
    assert report["parameter_update_check_passed"] is True
    assert report["gradient_check_passed"] is True
    assert report["optimizer_state_check_passed"] is True
    assert report["deterministic_replay_check_passed"] is True
    assert report["network_used"] is False
    assert report["package_install_attempted"] is False
    assert report["download_attempted"] is False
    assert report["dataset_download_attempted"] is False
    assert report["model_download_attempted"] is False
    assert report["torch_required"] is False
    assert report["gpu_required"] is False
    assert report["launch_ready"] is False
    assert report["launch_allowed"] is False


def test_tiny_real_training_smoke_cli_invalid_steps_fails_cleanly(tmp_path):
    report_path = tmp_path / "invalid-tiny-real-training-smoke.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "dev",
            "tiny-real-training-smoke",
            "--synthetic",
            "--model",
            "tiny-linear",
            "--steps",
            "2",
            "--optimizer",
            "adamw",
            "--out",
            str(report_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 1
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["tiny_real_training_smoke_status"] == "failed"
    assert report["failed_check"] == "argument_validation"
    assert report["launch_ready"] is False
    assert report["launch_allowed"] is False
