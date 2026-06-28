from __future__ import annotations

from decodilo.dev.learner_syncer_smoke import (
    load_learner_syncer_smoke_report,
    run_learner_syncer_smoke,
)


def test_learner_syncer_smoke_report_contains_exchange_step(tmp_path):
    report_path = tmp_path / "learner-syncer-smoke.json"

    report = run_learner_syncer_smoke(
        synthetic=True,
        max_steps=1,
        out=report_path,
    )
    loaded = load_learner_syncer_smoke_report(report_path)

    assert report.learner_syncer_smoke_status == "passed"
    assert loaded.learner_syncer_smoke_status == "passed"
    assert loaded.learner_check_passed is True
    assert loaded.syncer_check_passed is True
    assert loaded.learner_syncer_exchange_check_passed is True
    assert loaded.update_or_commit_check_passed is True
    assert loaded.replay_or_metric_check_passed is True
    assert loaded.artifact_or_report_check_passed is True
    assert loaded.synthetic_steps_requested == 1
    assert loaded.synthetic_steps_completed == 1
    assert loaded.synthetic_updates_produced == 1
    assert loaded.synthetic_updates_accepted == 1
    assert loaded.synthetic_updates_rejected == 0
    assert loaded.sync_rounds_completed == 1
    assert loaded.global_version_before == 0
    assert loaded.global_version_after == 1
    assert loaded.useful_synthetic_tokens == 13
    assert loaded.stale_update_count == 0
    assert loaded.duplicate_update_count == 1
    assert loaded.runtime_checks["event_log_event_count"] == 6
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
    assert loaded.artifact_bytes < 20_000


def test_learner_syncer_smoke_invalid_steps_is_bounded_failure(tmp_path):
    report_path = tmp_path / "learner-syncer-smoke-failed.json"

    report = run_learner_syncer_smoke(
        synthetic=True,
        max_steps=0,
        out=report_path,
    )

    assert report.learner_syncer_smoke_status == "failed"
    assert report.failed_check == "argument_validation"
    assert report.error_classification == "invalid_arguments"
    assert report.network_used is False
    assert report.download_attempted is False
    assert report.real_model_training_attempted is False
    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report_path.stat().st_size < 20_000
