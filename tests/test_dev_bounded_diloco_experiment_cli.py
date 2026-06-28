from __future__ import annotations

import json
import subprocess
import sys

import pytest


def _run_bounded_diloco_experiment(
    report_path,
    *extra_args: str,
) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "dev",
            "bounded-diloco-experiment",
            *extra_args,
            "--out",
            str(report_path),
        ],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )


def test_dev_bounded_diloco_experiment_cli_passes_offline(tmp_path):
    report_path = tmp_path / "bounded-diloco-experiment.json"

    completed = _run_bounded_diloco_experiment(
        report_path,
        "--synthetic",
        "--learners",
        "1",
        "--sync-rounds",
        "1",
        "--fragments",
        "2",
        "--inner-optimizer",
        "adamw",
        "--outer-optimizer",
        "nesterov",
        "--max-steps",
        "1",
    )

    assert completed.returncode == 0, completed.stderr
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["bounded_diloco_experiment_status"] == "passed"
    assert report["command"] == "dev bounded-diloco-experiment"
    assert report["synthetic"] is True
    assert report["learners_requested"] == 1
    assert report["learners_observed"] == 1
    assert report["sync_rounds_requested"] == 1
    assert report["sync_rounds_completed"] == 1
    assert report["fragments_requested"] == 2
    assert report["fragments_observed"] == 2
    assert report["max_steps"] == 1
    assert report["inner_optimizer_requested"] == "adamw"
    assert report["outer_optimizer_requested"] == "nesterov"
    assert report["optimization_fidelity"] == "bounded_synthetic_diloco_experiment"
    assert report["inner_optimizer_semantics"] == "adamw"
    assert report["outer_optimizer_semantics"] == "nesterov"
    assert report["parameter_fragment_semantics"] == "synthetic_vector_fragments"
    assert report["learner_syncer_exchange_check_passed"] is True
    assert report["update_or_commit_check_passed"] is True
    assert report["quorum_or_acceptance_check_passed"] is True
    assert report["pseudo_gradient_check_passed"] is True
    assert report["inner_adamw_check_passed"] is True
    assert report["outer_nesterov_check_passed"] is True
    assert report["optimizer_state_roundtrip_check_passed"] is True
    assert report["reference_value_check_passed"] is True
    assert report["fragment_update_check_passed"] is True
    assert report["fragment_merge_check_passed"] is True
    assert report["fragment_reconstruction_check_passed"] is True
    assert report["fragment_schedule_check_passed"] is True
    assert report["fragment_state_roundtrip_check_passed"] is True
    assert report["per_fragment_reference_check_passed"] is True
    assert report["global_reference_check_passed"] is True
    assert report["protocol_optimizer_link_check_passed"] is True
    assert report["optimizer_fragment_link_check_passed"] is True
    assert report["protocol_fragment_link_check_passed"] is True
    assert report["integrated_reference_check_passed"] is True
    assert report["replay_or_metric_check_passed"] is True
    assert report["artifact_or_report_check_passed"] is True
    assert report["max_abs_error"] == 0.0
    assert report["full_diloco_training_claimed"] is False
    assert report["real_model_training_claimed"] is False
    assert report["true_model_fragment_claimed"] is False
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


@pytest.mark.parametrize(
    ("args", "expected_error"),
    [
        (
            [
                "--synthetic",
                "--learners",
                "2",
                "--sync-rounds",
                "1",
                "--fragments",
                "2",
                "--inner-optimizer",
                "adamw",
                "--outer-optimizer",
                "nesterov",
                "--max-steps",
                "1",
            ],
            "requires --learners 1",
        ),
        (
            [
                "--synthetic",
                "--learners",
                "1",
                "--sync-rounds",
                "2",
                "--fragments",
                "2",
                "--inner-optimizer",
                "adamw",
                "--outer-optimizer",
                "nesterov",
                "--max-steps",
                "1",
            ],
            "requires --sync-rounds 1",
        ),
        (
            [
                "--synthetic",
                "--learners",
                "1",
                "--sync-rounds",
                "1",
                "--fragments",
                "3",
                "--inner-optimizer",
                "adamw",
                "--outer-optimizer",
                "nesterov",
                "--max-steps",
                "1",
            ],
            "requires --fragments 2",
        ),
        (
            [
                "--synthetic",
                "--learners",
                "1",
                "--sync-rounds",
                "1",
                "--fragments",
                "2",
                "--inner-optimizer",
                "sgd",
                "--outer-optimizer",
                "nesterov",
                "--max-steps",
                "1",
            ],
            "requires --inner-optimizer adamw",
        ),
        (
            [
                "--synthetic",
                "--learners",
                "1",
                "--sync-rounds",
                "1",
                "--fragments",
                "2",
                "--inner-optimizer",
                "adamw",
                "--outer-optimizer",
                "sgd",
                "--max-steps",
                "1",
            ],
            "requires --outer-optimizer nesterov",
        ),
        (
            [
                "--synthetic",
                "--learners",
                "1",
                "--sync-rounds",
                "1",
                "--fragments",
                "2",
                "--inner-optimizer",
                "adamw",
                "--outer-optimizer",
                "nesterov",
                "--max-steps",
                "2",
            ],
            "requires --max-steps 1",
        ),
    ],
)
def test_dev_bounded_diloco_experiment_invalid_args_fail_cleanly(
    tmp_path,
    args,
    expected_error,
):
    report_path = tmp_path / "invalid-bounded-diloco-experiment.json"

    completed = _run_bounded_diloco_experiment(report_path, *args)

    assert completed.returncode != 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["bounded_diloco_experiment_status"] == "failed"
    assert report["failed_check"] == "argument_validation"
    assert report["error_classification"] == "invalid_arguments"
    assert any(expected_error in error for error in report["errors"])
    assert report["network_used"] is False
    assert report["download_attempted"] is False
    assert report["training_attempted"] is False
    assert report["launch_ready"] is False
    assert report["launch_allowed"] is False
