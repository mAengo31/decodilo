from __future__ import annotations

from decodilo.dev.synthetic_experiment import (
    load_synthetic_experiment_report,
    run_synthetic_experiment,
)


def test_synthetic_experiment_report_contains_protocol_step(tmp_path):
    report_path = tmp_path / "synthetic-experiment.json"

    report = run_synthetic_experiment(
        synthetic=True,
        max_steps=1,
        out=report_path,
    )
    loaded = load_synthetic_experiment_report(report_path)

    assert report.synthetic_experiment_status == "passed"
    assert loaded.synthetic_experiment_status == "passed"
    assert loaded.learner_or_runtime_check_passed is True
    assert loaded.update_or_commit_check_passed is True
    assert loaded.replay_or_metric_check_passed is True
    assert loaded.artifact_or_report_check_passed is True
    assert loaded.useful_synthetic_steps == 1
    assert loaded.synthetic_updates_produced == 1
    assert loaded.synthetic_updates_accepted == 1
    assert loaded.runtime_checks["event_log_event_count"] == 5
    assert loaded.runtime_checks["sync_rounds_committed"] == 1
    assert loaded.runtime_checks["accepted_useful_tokens"] == 8
    assert loaded.network_used is False
    assert loaded.package_install_attempted is False
    assert loaded.download_attempted is False
    assert loaded.training_attempted is False
    assert loaded.real_model_training_attempted is False
    assert loaded.torch_required is False
    assert loaded.gpu_required is False
    assert loaded.background_process_started is False
    assert loaded.launch_ready is False
    assert loaded.launch_allowed is False
    assert report_path.stat().st_size == loaded.artifact_bytes
    assert loaded.artifact_bytes < 16_384


def test_synthetic_experiment_report_invalid_steps_is_bounded_failure(tmp_path):
    report_path = tmp_path / "synthetic-experiment-failed.json"

    report = run_synthetic_experiment(
        synthetic=True,
        max_steps=0,
        out=report_path,
    )

    assert report.synthetic_experiment_status == "failed"
    assert report.failed_check == "argument_validation"
    assert report.error_classification == "invalid_arguments"
    assert report.network_used is False
    assert report.download_attempted is False
    assert report.real_model_training_attempted is False
    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report_path.stat().st_size < 16_384
