from __future__ import annotations

import json
import subprocess
import sys


def test_dev_learner_syncer_smoke_cli_passes_offline(tmp_path):
    report_path = tmp_path / "learner-syncer-smoke.json"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "dev",
            "learner-syncer-smoke",
            "--synthetic",
            "--max-steps",
            "1",
            "--out",
            str(report_path),
        ],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["learner_syncer_smoke_status"] == "passed"
    assert report["command"] == "dev learner-syncer-smoke"
    assert report["synthetic"] is True
    assert report["max_steps"] == 1
    assert report["network_used"] is False
    assert report["package_install_attempted"] is False
    assert report["download_attempted"] is False
    assert report["training_attempted"] is False
    assert report["real_model_training_attempted"] is False
    assert report["torch_required"] is False
    assert report["gpu_required"] is False
    assert report["background_process_started"] is False
    assert report["learner_check_passed"] is True
    assert report["syncer_check_passed"] is True
    assert report["learner_syncer_exchange_check_passed"] is True
    assert report["update_or_commit_check_passed"] is True
    assert report["replay_or_metric_check_passed"] is True
    assert report["artifact_or_report_check_passed"] is True
    assert report["launch_ready"] is False
    assert report["launch_allowed"] is False
    assert report_path.stat().st_size < 20_000


def test_dev_learner_syncer_smoke_cli_invalid_max_steps_fails_cleanly(tmp_path):
    report_path = tmp_path / "learner-syncer-smoke-invalid.json"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "dev",
            "learner-syncer-smoke",
            "--synthetic",
            "--max-steps",
            "2",
            "--out",
            str(report_path),
        ],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )

    assert completed.returncode != 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["learner_syncer_smoke_status"] == "failed"
    assert report["failed_check"] == "argument_validation"
    assert report["error_classification"] == "invalid_arguments"
    assert report["network_used"] is False
    assert report["package_install_attempted"] is False
    assert report["download_attempted"] is False
    assert report["training_attempted"] is False
    assert report["real_model_training_attempted"] is False
    assert report["launch_ready"] is False
    assert report["launch_allowed"] is False
    assert report_path.stat().st_size < 20_000
