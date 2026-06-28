from __future__ import annotations

import json
import subprocess
import sys


def _run_parameter_fragment_smoke(
    report_path,
    *extra_args: str,
) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "dev",
            "parameter-fragment-smoke",
            *extra_args,
            "--out",
            str(report_path),
        ],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )


def test_dev_parameter_fragment_smoke_cli_passes_offline(tmp_path):
    report_path = tmp_path / "parameter-fragment-smoke.json"

    completed = _run_parameter_fragment_smoke(
        report_path,
        "--synthetic",
        "--fragments",
        "2",
        "--max-steps",
        "1",
    )

    assert completed.returncode == 0, completed.stderr
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["parameter_fragment_smoke_status"] == "passed"
    assert report["command"] == "dev parameter-fragment-smoke"
    assert report["synthetic"] is True
    assert report["fragments_requested"] == 2
    assert report["fragments_observed"] == 2
    assert report["max_steps"] == 1
    assert report["parameter_fragment_semantics"] == "synthetic_vector_fragments"
    assert report["parameter_fragment_semantics"] != "true_model_fragment"
    assert report["fragment_count"] == 2
    assert report["fragment_update_check_passed"] is True
    assert report["fragment_merge_check_passed"] is True
    assert report["fragment_reconstruction_check_passed"] is True
    assert report["fragment_schedule_check_passed"] is True
    assert report["fragment_state_roundtrip_check_passed"] is True
    assert report["per_fragment_reference_check_passed"] is True
    assert report["global_reference_check_passed"] is True
    assert report["max_abs_error"] == 0.0
    assert report["overlap_semantics"] == "not_exercised"
    assert report["quantization_semantics"] == "not_exercised"
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


def test_dev_parameter_fragment_smoke_cli_invalid_fragments_fails_cleanly(tmp_path):
    report_path = tmp_path / "invalid-fragments.json"

    completed = _run_parameter_fragment_smoke(
        report_path,
        "--synthetic",
        "--fragments",
        "3",
        "--max-steps",
        "1",
    )

    assert completed.returncode != 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["parameter_fragment_smoke_status"] == "failed"
    assert report["failed_check"] == "argument_validation"
    assert report["error_classification"] == "invalid_arguments"
    assert report["parameter_fragment_semantics"] == "not_exercised"
    assert report["launch_ready"] is False
    assert report["launch_allowed"] is False


def test_dev_parameter_fragment_smoke_cli_invalid_max_steps_fails_cleanly(tmp_path):
    report_path = tmp_path / "invalid-max-steps.json"

    completed = _run_parameter_fragment_smoke(
        report_path,
        "--synthetic",
        "--fragments",
        "2",
        "--max-steps",
        "2",
    )

    assert completed.returncode != 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["parameter_fragment_smoke_status"] == "failed"
    assert report["failed_check"] == "argument_validation"
    assert report["error_classification"] == "invalid_arguments"
