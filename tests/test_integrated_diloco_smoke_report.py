from __future__ import annotations

from decodilo.dev.integrated_diloco_smoke import (
    load_integrated_diloco_smoke_report,
    run_integrated_diloco_smoke,
)


def test_integrated_diloco_smoke_report_verifies_protocol_and_optimizer(tmp_path):
    report_path = tmp_path / "integrated-diloco-smoke.json"

    report = run_integrated_diloco_smoke(
        synthetic=True,
        learners=1,
        sync_rounds=1,
        inner_optimizer="adamw",
        outer_optimizer="nesterov",
        max_steps=1,
        out=report_path,
    )
    loaded = load_integrated_diloco_smoke_report(report_path)

    assert report.integrated_diloco_smoke_status == "passed"
    assert loaded.integrated_diloco_smoke_status == "passed"
    assert loaded.optimization_fidelity == "integrated_optimizer_protocol_smoke"
    assert loaded.inner_optimizer_semantics == "adamw"
    assert loaded.outer_optimizer_semantics == "nesterov"
    assert loaded.parameter_fragment_semantics == "not_exercised"
    assert loaded.learner_count_observed == 1
    assert loaded.sync_rounds_completed == 1
    assert loaded.learner_syncer_exchange_check_passed is True
    assert loaded.update_or_commit_check_passed is True
    assert loaded.replay_or_metric_check_passed is True
    assert loaded.protocol_optimizer_link_check_passed is True
    assert loaded.pseudo_gradient_check_passed is True
    assert loaded.inner_adamw_check_passed is True
    assert loaded.outer_nesterov_check_passed is True
    assert loaded.optimizer_state_roundtrip_check_passed is True
    assert loaded.reference_value_check_passed is True
    assert loaded.max_abs_error == 0.0
    assert loaded.training_attempted is False
    assert loaded.real_model_training_attempted is False
    assert loaded.torch_required is False
    assert loaded.gpu_required is False
    assert loaded.background_process_started is False
    assert loaded.launch_ready is False
    assert loaded.launch_allowed is False
    assert report_path.stat().st_size == loaded.artifact_bytes
    assert loaded.artifact_bytes < 32_768


def test_integrated_diloco_smoke_invalid_args_are_bounded_failure(tmp_path):
    report_path = tmp_path / "integrated-diloco-smoke-failed.json"

    report = run_integrated_diloco_smoke(
        synthetic=True,
        learners=1,
        sync_rounds=2,
        inner_optimizer="adamw",
        outer_optimizer="nesterov",
        max_steps=1,
        out=report_path,
    )

    assert report.integrated_diloco_smoke_status == "failed"
    assert report.failed_check == "argument_validation"
    assert report.error_classification == "invalid_arguments"
    assert report.optimization_fidelity == "not_verified"
    assert report.network_used is False
    assert report.download_attempted is False
    assert report.real_model_training_attempted is False
    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report_path.stat().st_size < 32_768
