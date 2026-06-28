from __future__ import annotations

import json
import subprocess
import sys


def _run_optimizer_smoke(report_path, *extra_args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "dev",
            "diloco-optimizer-smoke",
            *extra_args,
            "--out",
            str(report_path),
        ],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )


def test_dev_diloco_optimizer_smoke_cli_passes_offline(tmp_path):
    report_path = tmp_path / "diloco-optimizer-smoke.json"

    completed = _run_optimizer_smoke(
        report_path,
        "--synthetic",
        "--inner-optimizer",
        "adamw",
        "--outer-optimizer",
        "nesterov",
        "--max-steps",
        "1",
    )

    assert completed.returncode == 0, completed.stderr
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["diloco_optimizer_smoke_status"] == "passed"
    assert report["command"] == "dev diloco-optimizer-smoke"
    assert report["synthetic"] is True
    assert report["max_steps"] == 1
    assert report["inner_optimizer_requested"] == "adamw"
    assert report["outer_optimizer_requested"] == "nesterov"
    assert report["inner_optimizer_semantics"] == "adamw"
    assert report["outer_optimizer_semantics"] == "nesterov"
    assert report["optimization_fidelity"] == "optimizer_semantics_smoke"
    assert report["parameter_fragment_semantics"] == "not_exercised"
    assert report["pseudo_gradient_check_passed"] is True
    assert report["inner_adamw_check_passed"] is True
    assert report["outer_nesterov_check_passed"] is True
    assert report["optimizer_state_roundtrip_check_passed"] is True
    assert report["reference_value_check_passed"] is True
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


def test_dev_diloco_optimizer_smoke_cli_invalid_inner_fails_cleanly(tmp_path):
    report_path = tmp_path / "invalid-inner.json"

    completed = _run_optimizer_smoke(
        report_path,
        "--synthetic",
        "--inner-optimizer",
        "sgd",
        "--outer-optimizer",
        "nesterov",
        "--max-steps",
        "1",
    )

    assert completed.returncode != 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["diloco_optimizer_smoke_status"] == "failed"
    assert report["failed_check"] == "argument_validation"
    assert report["error_classification"] == "invalid_arguments"
    assert report["optimization_fidelity"] == "not_verified"
    assert report["launch_ready"] is False
    assert report["launch_allowed"] is False


def test_dev_diloco_optimizer_smoke_cli_invalid_outer_fails_cleanly(tmp_path):
    report_path = tmp_path / "invalid-outer.json"

    completed = _run_optimizer_smoke(
        report_path,
        "--synthetic",
        "--inner-optimizer",
        "adamw",
        "--outer-optimizer",
        "sgd",
        "--max-steps",
        "1",
    )

    assert completed.returncode != 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["diloco_optimizer_smoke_status"] == "failed"
    assert report["failed_check"] == "argument_validation"
    assert report["error_classification"] == "invalid_arguments"


def test_dev_diloco_optimizer_smoke_cli_invalid_max_steps_fails_cleanly(tmp_path):
    report_path = tmp_path / "invalid-max-steps.json"

    completed = _run_optimizer_smoke(
        report_path,
        "--synthetic",
        "--inner-optimizer",
        "adamw",
        "--outer-optimizer",
        "nesterov",
        "--max-steps",
        "2",
    )

    assert completed.returncode != 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["diloco_optimizer_smoke_status"] == "failed"
    assert report["failed_check"] == "argument_validation"
    assert report["error_classification"] == "invalid_arguments"
