from __future__ import annotations

from decodilo.dev.diloco_smoke import load_diloco_smoke_report, run_diloco_smoke


def test_diloco_smoke_report_contains_diloco_shaped_protocol_step(tmp_path):
    report_path = tmp_path / "diloco-smoke.json"

    report = run_diloco_smoke(
        synthetic=True,
        learners=1,
        sync_rounds=1,
        max_steps=1,
        out=report_path,
    )
    loaded = load_diloco_smoke_report(report_path)

    assert report.diloco_smoke_status == "passed"
    assert loaded.diloco_smoke_status == "passed"
    assert loaded.diloco_shape_check_passed is True
    assert loaded.learner_count_observed == 1
    assert loaded.syncer_role_check_passed is True
    assert loaded.learner_syncer_exchange_check_passed is True
    assert loaded.update_or_commit_check_passed is True
    assert loaded.replay_or_metric_check_passed is True
    assert loaded.artifact_or_report_check_passed is True
    assert loaded.sync_rounds_completed == 1
    assert loaded.global_version_before == 0
    assert loaded.global_version_after == 1
    assert loaded.synthetic_updates_produced == 1
    assert loaded.synthetic_updates_accepted == 1
    assert loaded.synthetic_updates_rejected == 0
    assert loaded.useful_synthetic_tokens == 21
    assert loaded.stale_update_count == 0
    assert loaded.duplicate_update_count == 0
    assert loaded.optimization_fidelity == "diloco_shaped_protocol_only"
    assert loaded.inner_optimizer_semantics == "synthetic_placeholder"
    assert loaded.outer_optimizer_semantics == "token_weighted_merge"
    assert loaded.parameter_fragment_semantics == "not_exercised"
    assert "full_diloco_optimizer_fidelity" in loaded.skipped_checks
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
    assert loaded.artifact_bytes < 32_768


def test_diloco_smoke_invalid_arguments_are_bounded_failure(tmp_path):
    report_path = tmp_path / "diloco-smoke-failed.json"

    report = run_diloco_smoke(
        synthetic=True,
        learners=2,
        sync_rounds=1,
        max_steps=1,
        out=report_path,
    )

    assert report.diloco_smoke_status == "failed"
    assert report.failed_check == "argument_validation"
    assert report.error_classification == "invalid_arguments"
    assert report.network_used is False
    assert report.download_attempted is False
    assert report.real_model_training_attempted is False
    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report_path.stat().st_size < 32_768
