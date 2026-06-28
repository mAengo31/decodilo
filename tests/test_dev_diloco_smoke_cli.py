from __future__ import annotations

import json
import subprocess
import sys


def test_dev_diloco_smoke_cli_passes_offline(tmp_path):
    report_path = tmp_path / "diloco-smoke.json"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "dev",
            "diloco-smoke",
            "--synthetic",
            "--learners",
            "1",
            "--sync-rounds",
            "1",
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
    assert report["diloco_smoke_status"] == "passed"
    assert report["command"] == "dev diloco-smoke"
    assert report["synthetic"] is True
    assert report["learners_requested"] == 1
    assert report["sync_rounds_requested"] == 1
    assert report["max_steps"] == 1
    assert report["optimization_fidelity"] == "diloco_shaped_protocol_only"
    assert report["inner_optimizer_semantics"] == "synthetic_placeholder"
    assert report["outer_optimizer_semantics"] == "token_weighted_merge"
    assert report["network_used"] is False
    assert report["package_install_attempted"] is False
    assert report["download_attempted"] is False
    assert report["training_attempted"] is False
    assert report["real_model_training_attempted"] is False
    assert report["torch_required"] is False
    assert report["gpu_required"] is False
    assert report["background_process_started"] is False
    assert report["diloco_shape_check_passed"] is True
    assert report["learner_count_observed"] == 1
    assert report["syncer_role_check_passed"] is True
    assert report["learner_syncer_exchange_check_passed"] is True
    assert report["update_or_commit_check_passed"] is True
    assert report["replay_or_metric_check_passed"] is True
    assert report["artifact_or_report_check_passed"] is True
    assert report["launch_ready"] is False
    assert report["launch_allowed"] is False
    assert report_path.stat().st_size < 32_768


def test_dev_diloco_smoke_cli_invalid_learners_fails_cleanly(tmp_path):
    report_path = tmp_path / "diloco-smoke-invalid-learners.json"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "dev",
            "diloco-smoke",
            "--synthetic",
            "--learners",
            "2",
            "--sync-rounds",
            "1",
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

    assert completed.returncode != 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["diloco_smoke_status"] == "failed"
    assert report["failed_check"] == "argument_validation"
    assert report["error_classification"] == "invalid_arguments"
    assert report["launch_ready"] is False
    assert report["launch_allowed"] is False


def test_dev_diloco_smoke_cli_invalid_sync_rounds_fails_cleanly(tmp_path):
    report_path = tmp_path / "diloco-smoke-invalid-sync-rounds.json"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "dev",
            "diloco-smoke",
            "--synthetic",
            "--learners",
            "1",
            "--sync-rounds",
            "2",
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

    assert completed.returncode != 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["diloco_smoke_status"] == "failed"
    assert report["failed_check"] == "argument_validation"
    assert report["error_classification"] == "invalid_arguments"


def test_dev_diloco_smoke_cli_invalid_max_steps_fails_cleanly(tmp_path):
    report_path = tmp_path / "diloco-smoke-invalid-max-steps.json"

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "dev",
            "diloco-smoke",
            "--synthetic",
            "--learners",
            "1",
            "--sync-rounds",
            "1",
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
    assert report["diloco_smoke_status"] == "failed"
    assert report["failed_check"] == "argument_validation"
    assert report["error_classification"] == "invalid_arguments"
