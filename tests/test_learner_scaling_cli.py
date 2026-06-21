import json
import subprocess
import sys

import pytest

from decodilo.scaling.learner_pods import LearnerPodScalingScenario


def test_scaling_learner_sweep_and_backend_targets_cli(tmp_path) -> None:
    report_path = tmp_path / "learner-sweep.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "scaling",
            "learner-sweep",
            "--mode",
            "fixed_total_compute",
            "--total-gpus",
            "8",
            "--candidate-learners",
            "1,2,4",
            "--per-gpu-token-rate",
            "1000",
            "--failure-rate-per-hour",
            "0.02",
            "--recovery-time-seconds",
            "300",
            "--training-duration-hours",
            "24",
            "--model-params",
            "1000000",
            "--bytes-per-param",
            "2",
            "--fragment-count",
            "8",
            "--chunk-size-mb",
            "1",
            "--sync-interval-steps",
            "500",
            "--local-step-seconds",
            "1",
            "--bandwidth-cap-gbps",
            "10",
            "--artifact-read-gbps",
            "20",
            "--artifact-write-gbps",
            "10",
            "--syncer-merge-gbps",
            "5",
            "--out",
            str(report_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    stdout = json.loads(completed.stdout)
    assert stdout["launch_allowed"] is False
    assert report_path.exists()

    targets_path = tmp_path / "targets.json"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "scaling",
            "backend-targets",
            "--scaling-report",
            str(report_path),
            "--out",
            str(targets_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    targets = json.loads(targets_path.read_text(encoding="utf-8"))
    assert targets["launch_ready"] is False
    assert targets["target_learner_count"] is not None


def test_scaling_optimize_pods_cli(tmp_path) -> None:
    scenario = LearnerPodScalingScenario(
        scenario_id="opt-cli",
        mode="expanding_compute",
        candidate_learner_counts=[1, 2],
        gpus_per_learner=1,
        training_duration_hours=1,
        model_parameter_count=1000,
        bytes_per_parameter=2,
        fragment_count=4,
        chunk_size_bytes=1024,
        sync_interval_steps=100,
        local_step_seconds=1,
        calibration_profile={
            "per_gpu_token_rate": 1000,
            "failure_rate_per_hour": 0.01,
            "recovery_time_seconds": 300,
        },
    )
    scenario_path = tmp_path / "scenario.json"
    scenario_path.write_text(scenario.stable_json(), encoding="utf-8")
    out = tmp_path / "optimized.json"

    subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "scaling",
            "optimize-pods",
            "--scenario-json",
            str(scenario_path),
            "--objective",
            "minimize_cost_per_adjusted_token",
            "--out",
            str(out),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert json.loads(out.read_text(encoding="utf-8"))["recommended_learner_count"] in {1, 2}


def test_quorum_grace_sweep_cli(tmp_path) -> None:
    out = tmp_path / "quorum.json"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "scaling",
            "quorum-grace-sweep",
            "--learners",
            "8",
            "--quorum-candidates",
            "2,4,8",
            "--grace-window-seconds",
            "0,1,5",
            "--failure-rate-per-hour",
            "0.02",
            "--speed-variance",
            "0.2",
            "--out",
            str(out),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["pareto_candidates"]


def test_scaling_cli_rejects_bad_input(tmp_path) -> None:
    failed = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "scaling",
            "learner-sweep",
            "--mode",
            "fixed_total_compute",
            "--candidate-learners",
            "1,2",
            "--per-gpu-token-rate",
            "1000",
            "--failure-rate-per-hour",
            "0.01",
            "--recovery-time-seconds",
            "300",
            "--training-duration-hours",
            "1",
            "--model-params",
            "1000",
            "--bytes-per-param",
            "2",
            "--fragment-count",
            "4",
            "--chunk-size-mb",
            "1",
            "--sync-interval-steps",
            "100",
            "--local-step-seconds",
            "1",
            "--out",
            str(tmp_path / "bad.json"),
        ],
        capture_output=True,
        text=True,
    )

    assert failed.returncode != 0


@pytest.mark.perf
@pytest.mark.integration
def test_learner_scaling_local_cli_small_run(tmp_path) -> None:
    out = tmp_path / "learner-local.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "decodilo.cli",
            "perf",
            "learner-scaling-local",
            "--workdir",
            str(tmp_path / "runs"),
            "--candidate-learners",
            "1",
            "--steps",
            "8",
            "--min-quorum-ratio",
            "1.0",
            "--out",
            str(out),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=45,
    )

    payload = json.loads(completed.stdout)
    assert payload["cases_completed"] == 1
    assert payload["cloud_state"] == {"launch_allowed": False, "launch_ready": False}
    assert "local-only" in payload["candidate_results"][0]["warnings"][0]

