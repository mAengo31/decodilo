from __future__ import annotations

import json
import subprocess
import sys


def _run_integrated_smoke(report_path, *extra_args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "dev",
            "integrated-diloco-smoke",
            *extra_args,
            "--out",
            str(report_path),
        ],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )


def test_dev_integrated_diloco_smoke_cli_passes_offline(tmp_path):
    report_path = tmp_path / "integrated-diloco-smoke.json"

    completed = _run_integrated_smoke(
        report_path,
        "--synthetic",
        "--learners",
        "1",
        "--sync-rounds",
        "1",
        "--inner-optimizer",
        "adamw",
        "--outer-optimizer",
        "nesterov",
        "--max-steps",
        "1",
    )

    assert completed.returncode == 0, completed.stderr
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["integrated_diloco_smoke_status"] == "passed"
    assert report["command"] == "dev integrated-diloco-smoke"
    assert report["synthetic"] is True
    assert report["learners_requested"] == 1
    assert report["sync_rounds_requested"] == 1
    assert report["max_steps"] == 1
    assert report["inner_optimizer_requested"] == "adamw"
    assert report["outer_optimizer_requested"] == "nesterov"
    assert report["optimization_fidelity"] == "integrated_optimizer_protocol_smoke"
    assert report["inner_optimizer_semantics"] == "adamw"
    assert report["outer_optimizer_semantics"] == "nesterov"
    assert report["parameter_fragment_semantics"] == "not_exercised"
    assert report["learner_syncer_exchange_check_passed"] is True
    assert report["update_or_commit_check_passed"] is True
    assert report["replay_or_metric_check_passed"] is True
    assert report["pseudo_gradient_check_passed"] is True
    assert report["inner_adamw_check_passed"] is True
    assert report["outer_nesterov_check_passed"] is True
    assert report["optimizer_state_roundtrip_check_passed"] is True
    assert report["reference_value_check_passed"] is True
    assert report["protocol_optimizer_link_check_passed"] is True
    assert report["network_used"] is False
    assert report["package_install_attempted"] is False
    assert report["download_attempted"] is False
    assert report["training_attempted"] is False
    assert report["real_model_training_attempted"] is False
    assert report["torch_required"] is False
    assert report["gpu_required"] is False
    assert report["background_process_started"] is False
    assert report["launch_ready"] is False
    assert report["launch_allowed"] is False
    assert report_path.stat().st_size < 32_768


def test_dev_integrated_diloco_smoke_cli_invalid_learners_fails_cleanly(tmp_path):
    report_path = tmp_path / "invalid-learners.json"

    completed = _run_integrated_smoke(
        report_path,
        "--synthetic",
        "--learners",
        "2",
        "--sync-rounds",
        "1",
        "--inner-optimizer",
        "adamw",
        "--outer-optimizer",
        "nesterov",
        "--max-steps",
        "1",
    )

    assert completed.returncode != 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["integrated_diloco_smoke_status"] == "failed"
    assert report["failed_check"] == "argument_validation"
    assert report["error_classification"] == "invalid_arguments"
    assert report["optimization_fidelity"] == "not_verified"
    assert report["launch_ready"] is False
    assert report["launch_allowed"] is False


def test_dev_integrated_diloco_smoke_cli_invalid_sync_rounds_fails_cleanly(tmp_path):
    report_path = tmp_path / "invalid-sync-rounds.json"

    completed = _run_integrated_smoke(
        report_path,
        "--synthetic",
        "--learners",
        "1",
        "--sync-rounds",
        "2",
        "--inner-optimizer",
        "adamw",
        "--outer-optimizer",
        "nesterov",
        "--max-steps",
        "1",
    )

    assert completed.returncode != 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["integrated_diloco_smoke_status"] == "failed"
    assert report["failed_check"] == "argument_validation"
    assert report["error_classification"] == "invalid_arguments"


def test_dev_integrated_diloco_smoke_cli_invalid_optimizer_fails_cleanly(tmp_path):
    report_path = tmp_path / "invalid-optimizer.json"

    completed = _run_integrated_smoke(
        report_path,
        "--synthetic",
        "--learners",
        "1",
        "--sync-rounds",
        "1",
        "--inner-optimizer",
        "sgd",
        "--outer-optimizer",
        "nesterov",
        "--max-steps",
        "1",
    )

    assert completed.returncode != 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["integrated_diloco_smoke_status"] == "failed"
    assert report["failed_check"] == "argument_validation"
    assert report["error_classification"] == "invalid_arguments"


def test_dev_integrated_diloco_smoke_cli_invalid_max_steps_fails_cleanly(tmp_path):
    report_path = tmp_path / "invalid-max-steps.json"

    completed = _run_integrated_smoke(
        report_path,
        "--synthetic",
        "--learners",
        "1",
        "--sync-rounds",
        "1",
        "--inner-optimizer",
        "adamw",
        "--outer-optimizer",
        "nesterov",
        "--max-steps",
        "2",
    )

    assert completed.returncode != 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["integrated_diloco_smoke_status"] == "failed"
    assert report["failed_check"] == "argument_validation"
    assert report["error_classification"] == "invalid_arguments"
