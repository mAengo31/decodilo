from __future__ import annotations

from lambda_m090_helpers import make_m089r_workdir

from decodilo.lambda_cloud.bounded_diloco_experiment_success_record import (
    build_lambda_bounded_diloco_experiment_success_record_from_paths,
)


def test_bounded_diloco_experiment_success_record_captures_m089r_success(tmp_path):
    report = build_lambda_bounded_diloco_experiment_success_record_from_paths(
        workdir=make_m089r_workdir(tmp_path),
    )

    assert report.success_status == "remote_bounded_synthetic_diloco_experiment_success"
    assert report.infrastructure_passed is True
    assert report.bounded_diloco_experiment_command_passed is True
    assert report.bounded_diloco_experiment_status == "passed"
    assert report.optimization_fidelity == "bounded_synthetic_diloco_experiment"
    assert report.inner_optimizer_semantics == "adamw"
    assert report.outer_optimizer_semantics == "nesterov"
    assert report.parameter_fragment_semantics == "synthetic_vector_fragments"
    assert report.learners_observed == 1
    assert report.sync_rounds_completed == 1
    assert report.fragments_observed == 2
    assert report.max_abs_error == 0.0
    assert report.full_diloco_training_claimed is False
    assert report.real_model_training_claimed is False
    assert report.true_model_fragment_claimed is False
    assert report.overlap_semantics == "not_exercised"
    assert report.quantization_semantics == "not_exercised"
    assert report.termination_verified is True
    assert report.final_instance_count == 0
    assert report.final_unmanaged_count == 0
    assert report.launch_ready is False
    assert report.launch_allowed is False
