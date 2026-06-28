from __future__ import annotations

from decodilo.dev.bounded_diloco_experiment import (
    load_bounded_diloco_experiment_report,
    run_bounded_diloco_experiment,
)


def test_bounded_diloco_experiment_report_verifies_complete_synthetic_flow(tmp_path):
    report_path = tmp_path / "bounded-diloco-experiment.json"

    report = run_bounded_diloco_experiment(
        synthetic=True,
        learners=1,
        sync_rounds=1,
        fragments=2,
        inner_optimizer="adamw",
        outer_optimizer="nesterov",
        max_steps=1,
        out=report_path,
    )
    loaded = load_bounded_diloco_experiment_report(report_path)

    assert report.bounded_diloco_experiment_status == "passed"
    assert loaded.bounded_diloco_experiment_status == "passed"
    assert loaded.optimization_fidelity == "bounded_synthetic_diloco_experiment"
    assert loaded.inner_optimizer_semantics == "adamw"
    assert loaded.outer_optimizer_semantics == "nesterov"
    assert loaded.parameter_fragment_semantics == "synthetic_vector_fragments"
    assert loaded.learners_observed == 1
    assert loaded.sync_rounds_completed == 1
    assert loaded.fragments_observed == 2
    assert loaded.fragment_count == 2
    assert loaded.learner_syncer_exchange_check_passed is True
    assert loaded.update_or_commit_check_passed is True
    assert loaded.quorum_or_acceptance_check_passed is True
    assert loaded.pseudo_gradient_check_passed is True
    assert loaded.inner_adamw_check_passed is True
    assert loaded.outer_nesterov_check_passed is True
    assert loaded.optimizer_state_roundtrip_check_passed is True
    assert loaded.reference_value_check_passed is True
    assert loaded.fragment_update_check_passed is True
    assert loaded.fragment_merge_check_passed is True
    assert loaded.fragment_reconstruction_check_passed is True
    assert loaded.fragment_schedule_check_passed is True
    assert loaded.fragment_state_roundtrip_check_passed is True
    assert loaded.per_fragment_reference_check_passed is True
    assert loaded.global_reference_check_passed is True
    assert loaded.protocol_optimizer_link_check_passed is True
    assert loaded.optimizer_fragment_link_check_passed is True
    assert loaded.protocol_fragment_link_check_passed is True
    assert loaded.integrated_reference_check_passed is True
    assert loaded.replay_or_metric_check_passed is True
    assert loaded.artifact_or_report_check_passed is True
    assert loaded.max_abs_error == 0.0
    assert loaded.full_diloco_training_claimed is False
    assert loaded.real_model_training_claimed is False
    assert loaded.true_model_fragment_claimed is False
    assert loaded.overlap_semantics == "not_exercised"
    assert loaded.quantization_semantics == "not_exercised"
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


def test_bounded_diloco_experiment_invalid_args_are_bounded_failure(tmp_path):
    report_path = tmp_path / "bounded-diloco-experiment-failed.json"

    report = run_bounded_diloco_experiment(
        synthetic=True,
        learners=1,
        sync_rounds=1,
        fragments=1,
        inner_optimizer="adamw",
        outer_optimizer="nesterov",
        max_steps=1,
        out=report_path,
    )

    assert report.bounded_diloco_experiment_status == "failed"
    assert report.failed_check == "argument_validation"
    assert report.error_classification == "invalid_arguments"
    assert report.optimization_fidelity == "not_verified"
    assert report.parameter_fragment_semantics == "not_exercised"
    assert report.network_used is False
    assert report.download_attempted is False
    assert report.real_model_training_attempted is False
    assert report.launch_ready is False
    assert report.launch_allowed is False
    assert report_path.stat().st_size < 32_768
